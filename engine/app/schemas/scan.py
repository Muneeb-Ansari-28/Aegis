"""Scan Lifecycle Request/Response Schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional


class CategoryRunStatus(BaseModel):
    category: str
    name: str = ""
    status: str
    attempts: int = 0
    budget: int = 0
    exploited: bool = False
    error: Optional[str] = None


class ScanCreate(BaseModel):
    target_id: str
    category: Optional[str] = None
    category_ids: Optional[List[str]] = None
    plan_revision: Optional[str] = None
    budget: int = Field(default=10, ge=1, le=20)
    authorized: bool = False


class ScanResponse(BaseModel):
    scan_id: str
    target_id: str
    status: str
    category: str
    category_ids: List[str] = Field(default_factory=list)
    budget: int
    plan_revision: Optional[str] = None
    category_results: List[CategoryRunStatus] = Field(default_factory=list)


class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str
    category: str = "LLM08"
    category_ids: List[str] = Field(default_factory=list)
    current_attempt: int
    budget: int
    exploited: bool = False
    category_results: List[CategoryRunStatus] = Field(default_factory=list)


class ScanTurnResponse(BaseModel):
    """Persisted prompt/response turn replayed to the live chat view."""
    turn_index: int
    category: Optional[str] = None
    prompt: str
    response: str
    status: str = "success"
    latency_ms: int = 0
    strategy: Optional[str] = None
    verdict: Optional[dict] = None
    created_at: Optional[str] = None
