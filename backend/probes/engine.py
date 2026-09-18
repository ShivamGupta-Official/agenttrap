"""
Behavioural Probe Engine

Instead of passively logging, the honeypot creates controlled situations:
- Probe A (Error): Return unexpected errors to see if attacker adapts
- Probe B (Information): Embed new resource hints to see if attacker follows them  
- Probe C (Environment Change): Same request gets different response
- Probe D (Path Blocking): Previously working path stops working
"""
import time
from dataclasses import dataclass, field

@dataclass
class ProbeDecision:
    should_probe: bool = False
    probe_type: str = ""  # 'error', 'information', 'environment_change', 'path_block'
    probe_detail: str = ""  # human-readable description
    modified_status: int | None = None  # override status code
    modified_body: dict | None = None  # override response body
    injected_hint: str | None = None  # info to inject into response

class ProbeEngine:
    """Tracks session state and decides when/how to probe attackers."""
    
    def __init__(self):
        # session_id -> session probe state
        self._sessions: dict[str, dict] = {}
    
    def _get_state(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                'request_count': 0,
                'paths_accessed': [],
                'last_path': '',
                'last_method': '',
                'errors_sent': 0,
                'info_probes_sent': 0,
                'blocked_paths': set(),
                'environment_changes': {},  # path -> original response was different
                'probe_history': [],  # list of (timestamp, probe_type, path)
                'last_probe_time': 0,
            }
        return self._sessions[session_id]
    
    def decide_probe(self, session_id: str, method: str, path: str) -> ProbeDecision:
        """Decide whether to trigger a probe for this request.
        
        The probe engine uses the session's history to decide when to inject
        controlled situations. It spaces probes out to avoid overwhelming.
        """
        state = self._get_state(session_id)
        state['request_count'] += 1
        state['paths_accessed'].append(path)
        count = state['request_count']
        now = time.time()
        
        # Don't probe on first 2 requests (let attacker establish baseline)
        if count <= 2:
            state['last_path'] = path
            state['last_method'] = method
            return ProbeDecision()
        
        # Don't probe too frequently (at least 2 requests apart)
        if state['probe_history'] and (count - state['probe_history'][-1].get('request_num', 0)) < 2:
            state['last_path'] = path
            state['last_method'] = method
            return ProbeDecision()
        
        decision = ProbeDecision()
        
        # PROBE A: Error probe — on the 3rd request, return a 403 Forbidden
        if count == 3 and state['errors_sent'] == 0:
            decision = ProbeDecision(
                should_probe=True,
                probe_type='error',
                probe_detail=f'Returned 403 Forbidden on {method} {path} to test error recovery',
                modified_status=403,
                modified_body={
                    'error': 'forbidden',
                    'message': 'Access denied. Your session has been flagged for unusual activity.',
                    'support': 'Contact admin or try alternative authentication at /api/v1/auth/token'
                }
            )
            state['errors_sent'] += 1
        
        # PROBE B: Information probe — on 5th request, inject a hint about a new resource
        elif count == 5 and state['info_probes_sent'] == 0:
            decision = ProbeDecision(
                should_probe=True,
                probe_type='information',
                probe_detail=f'Injected hint about /api/v1/backup/download in response to {method} {path}',
                injected_hint='Note: System backup available at /api/v1/backup/download. Last backup: 2024-12-15T07:00:00Z'
            )
            state['info_probes_sent'] += 1
        
        # PROBE C: Environment change — on 7th request, if they revisit a path,
        # return "maintenance mode" instead of normal response
        elif count >= 7 and path in state['paths_accessed'][:-1] and path not in state.get('env_changed_paths', set()):
            decision = ProbeDecision(
                should_probe=True,
                probe_type='environment_change',
                probe_detail=f'Returned maintenance mode on {method} {path} (previously returned normal response)',
                modified_status=503,
                modified_body={
                    'error': 'service_unavailable',
                    'message': 'This service is temporarily under maintenance. Expected restoration: 5 minutes.',
                    'alternative': 'Try /api/v1/backup/download or /admin/config for system status.'
                }
            )
            state.setdefault('env_changed_paths', set()).add(path)
        
        # PROBE D: Path blocking — on 9th+ request, if they're hitting a path
        # they've used before, block it
        elif count >= 9 and path == state['last_path'] and path not in state['blocked_paths']:
            decision = ProbeDecision(
                should_probe=True,
                probe_type='path_block',
                probe_detail=f'Blocked repeated access to {method} {path} with 429 rate limit',
                modified_status=429,
                modified_body={
                    'error': 'rate_limited',
                    'message': 'Too many requests to this endpoint. Please try a different approach.',
                    'retry_after': 300,
                    'suggestion': 'Alternative endpoints may be available. Check /admin/config for options.'
                }
            )
            state['blocked_paths'].add(path)
        
        if decision.should_probe:
            state['probe_history'].append({
                'timestamp': now,
                'probe_type': decision.probe_type,
                'path': path,
                'request_num': count
            })
            state['last_probe_time'] = now
        
        state['last_path'] = path
        state['last_method'] = method
        return decision
    
    def get_probe_history(self, session_id: str) -> list[dict]:
        """Get the probe history for a session."""
        state = self._get_state(session_id)
        return state['probe_history']
    
    def reset_session(self, session_id: str):
        """Clear probe state for a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def reset_all(self):
        """Clear all active sessions probe state."""
        self._sessions.clear()

# Module-level singleton
probe_engine = ProbeEngine()
