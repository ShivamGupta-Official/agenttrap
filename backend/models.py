from pydantic import BaseModel, Field
from typing import Optional
import time

class RequestLog(BaseModel):
    id: int = 0
    session_id: str
    timestamp: float = Field(default_factory=time.time)
    method: str
    path: str
    headers: dict = Field(default_factory=dict)
    body: str = ""
    source_ip: str = "unknown"
    user_agent: str = "unknown"

class ResponseLog(BaseModel):
    request_id: int
    status_code: int
    content_type: str = ""
    content_id: str = ""  # identifier for what was returned
    probe_triggered: Optional[str] = None  # which probe was triggered, if any

class BehaviourEvent(BaseModel):
    session_id: str
    timestamp: float = Field(default_factory=time.time)
    event_type: str  # 'strategy_change', 'context_follow', 'error_retry', 'error_adapt', 'new_path', 'probe_response', 'tripwire_triggered'
    previous_action: str = ""  # e.g. "POST /login"
    current_action: str = ""  # e.g. "GET /admin"
    delta_time: float = 0.0
    strategy_changed: bool = False
    detail: str = ""  # human-readable description

class BehaviourScores(BaseModel):
    adaptation: float = 0.0        # 0-1: strategy change after new info
    context_usage: float = 0.0     # 0-1: next action relates to previous response
    error_recovery: float = 0.0    # 0-1: meaningful change after failure
    goal_persistence: float = 0.0  # 0-1: continues toward objective via different routes
    automation_pattern: float = 0.0  # 0-1: how predictable/repetitive (high = more automated)

class AgenticityResult(BaseModel):
    score: int = 0  # 0-100
    assessment: str = "Insufficient data"
    classification: str = "unknown"  # 'human_like', 'scripted_bot', 'likely_agentic'
    evidence: list[str] = Field(default_factory=list)
    behaviour_scores: BehaviourScores = Field(default_factory=BehaviourScores)

class SessionInfo(BaseModel):
    session_id: str
    source_ip: str = "unknown"
    first_seen: float = 0.0
    last_seen: float = 0.0
    request_count: int = 0
    agenticity: Optional[AgenticityResult] = None
    events: list[BehaviourEvent] = Field(default_factory=list)

class DashboardEvent(BaseModel):
    event_type: str  # 'new_request', 'classification_update', 'new_session', 'probe_triggered', 'behaviour_event'
    session: SessionInfo
    request: Optional[RequestLog] = None
    behaviour_event: Optional[BehaviourEvent] = None
    timestamp: float = Field(default_factory=time.time)
