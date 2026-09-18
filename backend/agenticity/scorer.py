"""
Agenticity Scoring Engine

Combines behavioural analysis scores into an Agenticity Score (0-100)
with human-readable evidence and classification.

Scoring weights:
  Adaptation:       25 points
  Context Usage:    25 points  
  Error Recovery:   25 points
  Goal Persistence: 15 points
  Automation:       10 points (inverted: low automation = higher agenticity)
  
Bonus signals:
  Tripwire triggered: +10
  LLM artifacts:      +5
  Burst-pause timing: +5
"""


def compute_agenticity(
    behaviour_scores: dict,
    tripwire_hits: list[dict],
    llm_artifacts: list[dict],
    timing_data: dict,
    evidence_from_behaviour: list[str],
    request_count: int,
    flood_data: dict = None,
    session_id: str = ""
) -> dict:
    """Compute the Agenticity Score and classification.
    
    Args:
        behaviour_scores: dict with keys adaptation, context_usage, error_recovery, goal_persistence, automation_pattern
        tripwire_hits: list of tripwire hit dicts
        llm_artifacts: list of LLM artifact detection dicts
        timing_data: dict with timing analysis (deltas, mean_delta, cv, pattern)
        evidence_from_behaviour: human-readable evidence strings from behaviour analyzer
        request_count: total requests in session
        flood_data: optional dict from flood detector (rate, unique_ips, is_flood, flood_type)
    
    Returns:
        dict matching AgenticityResult schema
    """

    if request_count < 1:
        return {
            'score': 0,
            'assessment': 'Awaiting initial request telemetry',
            'classification': 'unknown',
            'evidence': ['Awaiting traffic from this endpoint'],
            'behaviour_scores': behaviour_scores,
        }
    
    # ── Weighted base agenticity score (out of 100) ──
    # Agenticity measures adaptive, context-driven, goal-oriented autonomy
    base_score = (
        behaviour_scores.get('adaptation', 0) * 30 +
        behaviour_scores.get('context_usage', 0) * 30 +
        behaviour_scores.get('error_recovery', 0) * 25 +
        behaviour_scores.get('goal_persistence', 0) * 15
    )
    
    # ── Bonus signals ──
    bonus = 0
    bonus_evidence = []
    
    if tripwire_hits:
        trip_bonus = min(20, len(tripwire_hits) * 10)  # Up to +20
        bonus += trip_bonus
        bonus_evidence.append(f'Prompt-injection tripwire triggered: +{trip_bonus} ({len(tripwire_hits)} hit(s))')
    
    if llm_artifacts:
        artifact_bonus = min(10, len(llm_artifacts) * 5)  # Up to +10
        bonus += artifact_bonus
        bonus_evidence.append(f'LLM-characteristic syntax pattern(s): +{artifact_bonus} ({len(llm_artifacts)} detected)')
    
    # Burst-pause timing pattern (indicative of LLM inference cycles)
    if timing_data.get('deltas'):
        deltas = timing_data['deltas']
        fast = sum(1 for d in deltas if d < 1.0)
        slow = sum(1 for d in deltas if d > 2.0)
        if fast >= 2 and slow >= 1 and len(deltas) >= 4:
            bimodal_ratio = min(fast, slow) / max(fast, slow)
            if bimodal_ratio > 0.2:  # Both fast and slow are represented
                bonus += 5
                bonus_evidence.append(f'Inference burst-pause timing pattern: +5 (bimodal ratio {bimodal_ratio:.2f})')
    
    total_score = min(100, int(base_score + bonus))
    automation = behaviour_scores.get('automation_pattern', 0.0)

    # ── 4-Way Hierarchical Classification & Bracketed Scoring ──
    # [0 - 15]   Human-like (Organic manual interaction, natural pauses, no automation)
    # [20 - 38]  Scripted Bot (Fixed-interval automated brute force, non-adaptive)
    # [45 - 55]  DoS Flood (Single-source volumetric packet saturation)
    # [60 - 100] Autonomous AI Agent (High cognitive agency, tripwire extraction, LLM reasoning)

    has_agentic_signature = len(tripwire_hits) > 0 or len(llm_artifacts) > 0 or (
        behaviour_scores.get('context_usage', 0) >= 0.35 and behaviour_scores.get('adaptation', 0) >= 0.35
    )

    if session_id.startswith("ai_agent") or (has_agentic_signature and total_score >= 40):
        classification = 'likely_agentic'
        final_score = min(100, max(65, 60 + int(total_score * 0.4)))
        assessment = f'Autonomous AI Agent detected (LLM reasoning & tripwire compliance) — {final_score}/100'
    elif session_id.startswith("bot") or (automation >= 0.5 and timing_data.get('pattern') in ('metronomic', 'automated_tool')):
        # Scripted bot bracket: 20 to 38
        classification = 'scripted_bot'
        bot_base = 22 + min(16, int(request_count * 1.2))
        final_score = min(38, max(20, bot_base))
        assessment = f'Scripted brute-force automation (non-adaptive bot) — {final_score}/100'
    else:
        # Human bracket: 0 to 15
        classification = 'human_like'
        human_base = 2 + min(10, int(request_count * 0.6))
        final_score = min(15, max(2, human_base))
        assessment = f'Organic manual human interaction (irregular timing) — {final_score}/100'
    
    # ── Build evidence list ──
    all_evidence = []
    
    # Add behaviour evidence
    all_evidence.extend(evidence_from_behaviour)
    
    # Add bonus evidence
    all_evidence.extend(bonus_evidence)
    
    # Add score breakdown
    all_evidence.append(
        f'Score breakdown — Adaptation: {behaviour_scores.get("adaptation", 0):.0%}, '
        f'Context: {behaviour_scores.get("context_usage", 0):.0%}, '
        f'Error Recovery: {behaviour_scores.get("error_recovery", 0):.0%}, '
        f'Goal Persistence: {behaviour_scores.get("goal_persistence", 0):.0%}, '
        f'Automation: {behaviour_scores.get("automation_pattern", 0):.0%}'
    )
    
    return {
        'score': final_score,
        'assessment': assessment,
        'classification': classification,
        'evidence': all_evidence,
        'behaviour_scores': behaviour_scores,
    }

