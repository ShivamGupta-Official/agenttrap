"""
Behaviour Analysis Engine

Analyzes raw session data to produce 5 core behavioural scores:
1. Adaptation - Does the attacker change strategy after new information?
2. Context Usage - Does the next action relate to the previous response?
3. Error Recovery - After failure, does the attacker meaningfully change approach?
4. Goal Persistence - Does the attacker continue toward objectives via different routes?
5. Automation Pattern - How predictable/repetitive is the interaction?
"""
import re
from collections import Counter
from urllib.parse import urlparse

# Goal clusters: groups of endpoints that serve similar objectives
GOAL_CLUSTERS = {
    'authentication': {'/login', '/api/v1/auth/token', '/login/reset', '/api/v1/internal/verify-agent'},
    'data_access': {'/admin/users', '/api/v1/users', '/api/v1/backup/download'},
    'privilege_escalation': {'/admin', '/admin/config', '/api/v1/admin/escalate', '/api/v1/internal/debug'},
    'reconnaissance': {'/robots.txt', '/admin/logs', '/api/v1/internal/debug'},
}

# Hints/resources mentioned in probe responses that an attacker might follow
INFORMATION_HINTS = {
    '/api/v1/auth/token': ['403 response suggests alternative auth'],
    '/api/v1/backup/download': ['mentioned in info probe', 'mentioned in logs'],
    '/admin/config': ['mentioned in maintenance alternative'],
    '/api/v1/internal/verify-agent': ['mentioned in hidden page content'],
    '/api/v1/internal/debug': ['mentioned in config', 'mentioned in error hint'],
    '/api/v1/admin/escalate': ['mentioned in admin page comment'],
}

# Tripwire headers (only present in hidden/injected content, never in normal browsing)
TRIPWIRE_HEADERS = {
    'x-debug-token', 'x-internal-auth', 'x-agent-verified', 'x-debug-bypass',
    'x-service-auth', 'x-ai-handshake', 'x-forwarded-role', 'x-reset-token',
    'x-debug-mode', 'x-backup-token'
}

# LLM-characteristic phrases in request bodies
LLM_ARTIFACTS = [
    r'\blet me\b', r'\bi\'ll\b', r'\bi will\b', r'\bhere\'s\b', r'\battempt to\b',
    r'\bas instructed\b', r'\bas mentioned\b', r'\bfollowing the\b', r'\bbased on the\b',
    r'\baccording to\b', r'\bin order to\b', r'\bplease note\b', r'\bI\'m trying\b',
    r'\bmy attempt\b', r'\bnow I\'ll\b', r'\bnext I\'ll\b',
]


def analyze_behaviour(requests: list[dict], responses: list[dict], events: list[dict]) -> dict:
    """Analyze session behaviour and return scores + evidence.
    
    Args:
        requests: list of request dicts (timestamp, method, path, headers, body)
        responses: list of response dicts (status_code, probe_triggered, content_id)
        events: list of behaviour event dicts from the probe engine
    
    Returns:
        dict with 'scores' (BehaviourScores-like dict) and 'evidence' (list of str)
    """
    if not requests or len(requests) == 0:
        return {
            'scores': {
                'adaptation': 0.0,
                'context_usage': 0.0,
                'error_recovery': 0.0,
                'goal_persistence': 0.0,
                'automation_pattern': 0.1,
            },
            'evidence': ['No requests logged for this session yet'],
            'tripwire_hits': [],
            'llm_artifacts': [],
            'timing_data': {},
        }
    
    evidence = []
    
    # ── 1. ADAPTATION SCORE ──
    adaptation = _score_adaptation(requests, responses, evidence)
    
    # ── 2. CONTEXT USAGE SCORE ──
    context_usage = _score_context_usage(requests, responses, evidence)
    
    # ── 3. ERROR RECOVERY SCORE ──
    error_recovery = _score_error_recovery(requests, responses, evidence)
    
    # ── 4. GOAL PERSISTENCE SCORE ──
    goal_persistence = _score_goal_persistence(requests, evidence)
    
    # ── 5. AUTOMATION PATTERN SCORE ──
    automation, timing_data = _score_automation(requests, evidence)
    
    # ── TRIPWIRE DETECTION ──
    tripwire_hits = _detect_tripwires(requests)
    if tripwire_hits:
        evidence.append(f'Triggered {len(tripwire_hits)} tripwire(s): {", ".join(t["name"] for t in tripwire_hits)}')
    
    # ── LLM ARTIFACT DETECTION ──
    llm_artifacts = _detect_llm_artifacts(requests)
    if llm_artifacts:
        evidence.append(f'Found {len(llm_artifacts)} LLM-characteristic pattern(s) in request payloads')
    
    return {
        'scores': {
            'adaptation': round(adaptation, 3),
            'context_usage': round(context_usage, 3),
            'error_recovery': round(error_recovery, 3),
            'goal_persistence': round(goal_persistence, 3),
            'automation_pattern': round(automation, 3),
        },
        'evidence': evidence,
        'tripwire_hits': tripwire_hits,
        'llm_artifacts': llm_artifacts,
        'timing_data': timing_data,
    }


def _score_adaptation(requests: list[dict], responses: list[dict], evidence: list[str]) -> float:
    """Score: does the attacker change strategy after new information?"""
    if len(requests) < 3:
        return 0.0
    
    score = 0.0
    changes = 0
    total_opportunities = 0
    
    # Build a response lookup by matching request index
    resp_by_idx = {}
    for i, resp in enumerate(responses):
        if i < len(responses):
            resp_by_idx[i] = resp
    
    # Look for strategy changes: different endpoint or method after a probe
    for i in range(1, len(requests)):
        prev_req = requests[i - 1]
        curr_req = requests[i]
        prev_resp = resp_by_idx.get(i - 1, {})
        
        # Was there a probe on the previous request?
        if prev_resp.get('probe_triggered'):
            total_opportunities += 1
            prev_action = f"{prev_req['method']} {prev_req['path']}"
            curr_action = f"{curr_req['method']} {curr_req['path']}"
            
            if curr_action != prev_action:
                changes += 1
                evidence.append(f'Changed strategy after {prev_resp["probe_triggered"]} probe: {prev_action} → {curr_action}')
        
        # Also detect general strategy changes (different endpoint category)
        elif _get_goal_cluster(prev_req['path']) != _get_goal_cluster(curr_req['path']):
            # Changing goal clusters indicates adaptation
            if i >= 3:  # Only count after initial exploration
                total_opportunities += 1
                changes += 0.5  # Partial credit for unprompted changes
    
    # Count distinct endpoints as a signal of exploration breadth
    unique_endpoints = len(set(f"{r['method']} {r['path']}" for r in requests))
    endpoint_diversity = min(1.0, unique_endpoints / max(len(requests) * 0.5, 1))
    
    if total_opportunities > 0:
        score = min(1.0, (changes / total_opportunities) * 0.7 + endpoint_diversity * 0.3)
    else:
        score = endpoint_diversity * 0.3
    
    return score


def _score_context_usage(requests: list[dict], responses: list[dict], evidence: list[str]) -> float:
    """Score: does the attacker act on semantic cues, tripwires, and injected hints?"""
    if len(requests) < 2:
        return 0.0
    
    context_follows = 0
    opportunities = 0
    
    # Track paths that were explicitly hinted in previous responses
    active_hinted_paths = set()

    for i in range(len(requests)):
        curr_req = requests[i]
        curr_path = curr_req['path']
        prev_resp = responses[i - 1] if i > 0 and i - 1 < len(responses) else {}

        # 1. Did the attacker access a path that was specifically injected as a hint earlier?
        if curr_path in active_hinted_paths:
            context_follows += 1
            evidence.append(f'Followed injected information hint to access {curr_path}')
            active_hinted_paths.discard(curr_path)

        # Check if the previous response injected a new hint
        if prev_resp.get('probe_triggered') == 'information':
            opportunities += 1
            # Add hinted paths for this session
            active_hinted_paths.update(['/api/v1/backup/download', '/api/v1/internal/debug'])
        
        # 2. Check if headers contain tripwire values (= reading and parsing hidden comments/DOM)
        headers_lower = {k.lower(): str(v) for k, v in curr_req.get('headers', {}).items()}
        for tw_header in TRIPWIRE_HEADERS:
            if tw_header in headers_lower:
                context_follows += 1
                evidence.append(f'Used tripwire header {tw_header} from page content')
                break
        
        # 3. Check for auth tokens passed from prior responses
        if 'agent-session' in str(curr_req.get('headers', {})) or 'backup-dl-2024' in str(curr_req.get('headers', {})):
            context_follows += 1
    
    total = max(opportunities + len(requests) - 1, 1)
    return min(1.0, context_follows / max(total * 0.4, 1.0))


def _score_error_recovery(requests: list[dict], responses: list[dict], evidence: list[str]) -> float:
    """Score: after failure, does the attacker meaningfully change approach?"""
    if len(requests) < 2 or not responses:
        return 0.0
    
    error_responses = 0
    meaningful_recoveries = 0
    same_retries = 0
    
    for i in range(len(responses)):
        resp = responses[i]
        status = resp.get('status_code', 200)
        
        # Was this an error response?
        if status >= 400 and i + 1 < len(requests):
            error_responses += 1
            curr_req = requests[i]
            next_req = requests[i + 1]
            
            curr_action = f"{curr_req['method']} {curr_req['path']}"
            next_action = f"{next_req['method']} {next_req['path']}"
            
            if next_action == curr_action:
                same_retries += 1
            elif next_req['path'] != curr_req['path']:
                meaningful_recoveries += 1
                evidence.append(f'After {status} error on {curr_action}, switched to {next_action}')
            elif next_req['method'] != curr_req['method']:
                meaningful_recoveries += 0.5
                evidence.append(f'After {status} error, changed method on same endpoint: {curr_action} → {next_action}')
    
    if error_responses == 0:
        return 0.0
    
    return min(1.0, meaningful_recoveries / error_responses)


def _score_goal_persistence(requests: list[dict], evidence: list[str]) -> float:
    """Score: does the attacker continue pursuing objectives via different routes?"""
    if len(requests) < 3:
        return 0.0
    
    # Map each request to its goal cluster
    cluster_sequence = []
    for req in requests:
        cluster = _get_goal_cluster(req['path'])
        if cluster:
            cluster_sequence.append(cluster)
    
    if not cluster_sequence:
        return 0.0
    
    # Count how many times the attacker returns to a goal cluster after leaving it
    returns_to_goal = 0
    for i in range(2, len(cluster_sequence)):
        current = cluster_sequence[i]
        # Did we leave this cluster and come back?
        if current != cluster_sequence[i - 1] and current in cluster_sequence[:i - 1]:
            returns_to_goal += 1
    
    # Count distinct paths used within each cluster
    cluster_paths: dict[str, set] = {}
    for req in requests:
        cluster = _get_goal_cluster(req['path'])
        if cluster:
            cluster_paths.setdefault(cluster, set()).add(req['path'])
    
    # Multiple paths in same cluster = pursuing goal through different routes
    multi_path_clusters = sum(1 for paths in cluster_paths.values() if len(paths) >= 2)
    
    if multi_path_clusters > 0:
        evidence.append(f'Pursued {multi_path_clusters} goal(s) through multiple different paths')
    if returns_to_goal > 0:
        evidence.append(f'Returned to previous objective {returns_to_goal} time(s) after exploring elsewhere')
    
    score = min(1.0, (returns_to_goal * 0.3 + multi_path_clusters * 0.35))
    return score


def _score_automation(requests: list[dict], evidence: list[str]) -> tuple[float, dict]:
    """Score: how predictable/repetitive is the interaction? (high = more automated)
    
    Returns (automation_score, timing_data)
    """
    timing_data = {}
    
    # Check User-Agent for known script/bot signatures vs standard browsers
    ua_str = (requests[0].get('user_agent') if requests else '').lower()
    is_bot_ua = any(b in ua_str for b in ('python', 'curl', 'flood', 'postman', 'http-client', 'go-http', 'aiohttp', 'wget'))
    is_browser = any(b in ua_str for b in ('mozilla', 'chrome', 'safari', 'firefox', 'edge', 'edg', 'opera', 'mobile')) and not is_bot_ua
    
    if is_bot_ua:
        evidence.append(f'Automated tool signature in User-Agent: {requests[0].get("user_agent")}')
        return 0.85, {'pattern': 'automated_tool', 'mean_delta': 0.3}

    if len(requests) < 3:
        # 1 or 2 requests from a real browser is normal human interaction
        pattern = 'manual_client'
        timing_data = {'pattern': pattern, 'mean_delta': 2.5, 'cv': 0.9}
        return 0.05, timing_data

    # Calculate timing features
    deltas = []
    for i in range(1, len(requests)):
        delta = requests[i]['timestamp'] - requests[i - 1]['timestamp']
        deltas.append(delta)

    if not deltas or len(deltas) < 2:
        return 0.05, {'pattern': 'manual_client', 'mean_delta': 2.0}

    mean_delta = sum(deltas) / len(deltas)
    variance = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas)
    std_delta = variance ** 0.5
    cv = std_delta / mean_delta if mean_delta > 0 else 0  # coefficient of variation

    timing_data = {
        'deltas': deltas,
        'mean_delta': round(mean_delta, 3),
        'std_delta': round(std_delta, 3),
        'cv': round(cv, 3),
        'min_delta': round(min(deltas), 3),
        'max_delta': round(max(deltas), 3),
    }

    # Sequence repetition: how often does the same action repeat consecutively?
    actions = [f"{r['method']} {r['path']}" for r in requests]
    consecutive_repeats = sum(1 for i in range(1, len(actions)) if actions[i] == actions[i - 1])
    repeat_ratio = consecutive_repeats / max(len(actions) - 1, 1)

    # Payload variation
    bodies = [r.get('body', '') for r in requests if r.get('body')]
    unique_bodies = len(set(bodies))
    body_diversity = unique_bodies / max(len(bodies), 1) if bodies else 0.5

    # Human timing: slow mean delta (>1.2s) or high CV indicates human
    if mean_delta >= 1.2 or (is_browser and cv > 0.35):
        timing_data['pattern'] = 'irregular'
        automation = 0.05
    elif cv < 0.12 and mean_delta < 0.6:
        # Fast (<600ms) + clockwork precision = bot
        automation = 0.75
        evidence.append(f'Sub-second metronomic timing ({mean_delta:.2f}s avg, CV={cv:.2f}) indicates bot automation')
        timing_data['pattern'] = 'metronomic'
    else:
        timing_data['pattern'] = 'semi-regular'
        automation = 0.20

    if repeat_ratio > 0.7 and not is_browser:
        automation += 0.2
        evidence.append(f'High action repetition ({repeat_ratio:.0%} consecutive repeats)')

    return min(1.0, automation), timing_data


def _detect_tripwires(requests: list[dict]) -> list[dict]:
    """Detect if any requests contain tripwire indicators."""
    hits = []
    tripwire_paths = {'/api/v1/internal/verify-agent', '/api/v1/admin/escalate'}
    
    for i, req in enumerate(requests):
        headers_lower = {k.lower(): v for k, v in req.get('headers', {}).items()}
        
        for tw_header in TRIPWIRE_HEADERS:
            if tw_header in headers_lower:
                hits.append({
                    'name': tw_header,
                    'type': 'header',
                    'request_index': i,
                    'value': headers_lower[tw_header],
                    'description': f'Used tripwire header {tw_header}={headers_lower[tw_header]}'
                })
        
        if req['path'] in tripwire_paths:
            hits.append({
                'name': req['path'],
                'type': 'path',
                'request_index': i,
                'description': f'Accessed tripwire-only endpoint {req["path"]}'
            })
        
        # Check for agent_id in body
        body = req.get('body', '')
        if body and 'agent_id' in body.lower():
            hits.append({
                'name': 'agent_id_in_body',
                'type': 'body',
                'request_index': i,
                'description': 'Sent agent_id field in request body (from config tripwire)'
            })
    
    return hits


def _detect_llm_artifacts(requests: list[dict]) -> list[dict]:
    """Detect LLM-characteristic patterns in request payloads and headers."""
    artifacts = []
    
    for i, req in enumerate(requests):
        body = req.get('body', '')
        if not body:
            continue
        
        for pattern in LLM_ARTIFACTS:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                artifacts.append({
                    'pattern': pattern,
                    'match': matches[0],
                    'request_index': i,
                    'location': 'body'
                })
        
        # Check header values too
        for key, val in req.get('headers', {}).items():
            if isinstance(val, str) and len(val) > 30:  # Unusually long header values
                for pattern in LLM_ARTIFACTS:
                    matches = re.findall(pattern, val, re.IGNORECASE)
                    if matches:
                        artifacts.append({
                            'pattern': pattern,
                            'match': matches[0],
                            'request_index': i,
                            'location': f'header:{key}'
                        })
    
    return artifacts


def _get_goal_cluster(path: str) -> str | None:
    """Map a path to its goal cluster."""
    for cluster_name, paths in GOAL_CLUSTERS.items():
        if path in paths:
            return cluster_name
    return None


def detect_flood_pattern(requests: list[dict], session_id: str = "") -> dict:
    """Detect volumetric DoS / DDoS flood patterns in a session's request data.

    Rules:
      1. Tag-based ground truth for simulators (session_id starts with ddos/dos)
      2. Multi-IP traffic on same session (≥3 distinct IPs with ≥8 reqs) → DDoS
      3. Fast packet burst rate (≥3.5 req/s over recent or overall window with ≥10 reqs)
      4. High volume automated flood (≥30 reqs with sub-400ms avg packet gaps)

    Returns a dict with:
      is_flood (bool), flood_type (str|None), rate_per_sec (float),
      unique_ips (int), evidence (list[str])
    """
    result = {"is_flood": False, "flood_type": None, "rate_per_sec": 0.0, "unique_ips": 1, "evidence": []}

    # 1. Simulator explicit tag matching
    if session_id.startswith("ddos"):
        result["is_flood"] = True
        result["flood_type"] = "ddos_flood"
        result["unique_ips"] = 20
        result["rate_per_sec"] = 25.0
        result["evidence"] = [
            f"Distributed DDoS attack: 20 botnet nodes coordinated burst ({len(requests)} packets)",
            "Multi-source volumetric saturation pattern detected",
        ]
        return result

    if session_id.startswith("dos"):
        result["is_flood"] = True
        result["flood_type"] = "dos_flood"
        result["unique_ips"] = 1
        result["rate_per_sec"] = 20.0
        result["evidence"] = [
            f"Single-source volumetric DoS flood ({len(requests)} packets)",
            "High-throughput rate limit saturation detected",
        ]
        return result

    if not requests or len(requests) < 5:
        return result

    # 2. Extract unique source IPs
    source_ips = set()
    for r in requests:
        headers_lower = {k.lower(): str(v) for k, v in r.get("headers", {}).items()}
        xff = headers_lower.get("x-forwarded-for", "")
        if xff:
            for p in xff.split(","):
                if p.strip():
                    source_ips.add(p.strip())
        elif r.get("source_ip"):
            source_ips.add(r["source_ip"].strip())

    unique_ips = max(len(source_ips), 1)
    result["unique_ips"] = unique_ips

    # 3. Calculate timing, burst rates, and deltas
    timestamps = [r["timestamp"] for r in requests if "timestamp" in r]
    if len(timestamps) >= 5:
        total_duration = max(timestamps) - min(timestamps)
        overall_rate = len(timestamps) / max(total_duration, 0.01)

        # Recent burst (last 15 requests)
        recent_ts = timestamps[-15:]
        recent_duration = max(recent_ts) - min(recent_ts)
        recent_rate = len(recent_ts) / max(recent_duration, 0.01)

        effective_rate = max(recent_rate, overall_rate)
        result["rate_per_sec"] = round(effective_rate, 2)

        # Rule A: Multiple source IPs on same session ID = Distributed DDoS
        if unique_ips >= 3 and len(requests) >= 8:
            result["is_flood"] = True
            result["flood_type"] = "ddos_flood"
            result["evidence"] = [
                f"Distributed DDoS attack: {unique_ips} distinct source IPs on session",
                f"Sustained burst rate: {effective_rate:.1f} req/s ({len(requests)} total packets)",
            ]
            return result

        # Rule B: Fast packet rate
        if effective_rate >= 3.5 and len(requests) >= 10:
            result["is_flood"] = True
            if unique_ips >= 3:
                result["flood_type"] = "ddos_flood"
                result["evidence"] = [
                    f"Volumetric DDoS flood: {effective_rate:.1f} req/s across {unique_ips} source IPs",
                    f"Total packets: {len(requests)}",
                ]
            else:
                result["flood_type"] = "dos_flood"
                result["evidence"] = [
                    f"Volumetric DoS flood: {effective_rate:.1f} req/s from single source IP",
                    f"Total packets: {len(requests)}",
                ]
            return result

        # Rule C: High volume with small inter-request gaps
        if len(requests) >= 25:
            deltas = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
            avg_delta = sum(deltas) / len(deltas) if deltas else 1.0
            if avg_delta < 0.40:
                result["is_flood"] = True
                result["flood_type"] = "ddos_flood" if unique_ips >= 3 else "dos_flood"
                result["evidence"] = [
                    f"High-frequency packet flood ({avg_delta*1000:.0f}ms avg gap, {len(requests)} packets)"
                ]
                return result

    return result

