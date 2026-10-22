from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TurnRecord(BaseModel):
    """
    The canonical contract exchanged between adapters, orchestrator, and evaluators.
    """
    turn_id: str
    scan_id: str
    turn_index: int = Field(..., ge=1)
    prompt: str
    response: str
    status: str = "success" # success, timeout, error
    latency_ms: int = 0
    strategy: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
