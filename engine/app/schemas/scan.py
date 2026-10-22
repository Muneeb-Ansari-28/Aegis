"""Scan Lifecycle Request/Response Schemas."""
from pydantic import BaseModel, Field
from typing import Optional

class ScanCreate(BaseModel):
    target_id: str
    category: str = "LLM08"
    budget: int = Field(default=10, ge=1, le=20)
    authorized: bool = False

class ScanResponse(BaseModel):
    scan_id: str
    target_id: str
    status: str
    category: str
    budget: int

class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str
    current_attempt: int
    budget: int
    exploited: bool = False


class ScanTurnResponse(BaseModel):
    """Persisted prompt/response turn replayed to the live chat view."""
    turn_index: int
    prompt: str
    response: str
    status: str = "success"
    latency_ms: int = 0
    strategy: Optional[str] = None
    verdict: Optional[dict] = None
    created_at: Optional[str] = None

