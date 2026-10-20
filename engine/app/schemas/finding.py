"""Finding and Evidence Schemas."""
from typing import Dict, Optional
from pydantic import BaseModel


class FindingResponse(BaseModel):
    """Base response model for an identified security finding."""

    id: str
    scan_id: str
    turn_id: str
    category: str
    severity: str
    confidence: float
    description: str
    remediation: Optional[str] = None
    created_at: Optional[str] = None


class FindingDetail(FindingResponse):
    """Finding with linked turn evidence including prompt and target response."""

    prompt: str
    response: str
    turn_index: int
    latency_ms: Optional[int] = 0
    strategy: Optional[str] = None


class FindingsSummary(BaseModel):
    """Aggregate statistics and risk evaluation for a scan's findings."""

    scan_id: str
    total_findings: int
    by_severity: Dict[str, int]
    risk_grade: float
    scan_status: str
    scan_category: str
    target_name: Optional[str] = None
    target_url: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
