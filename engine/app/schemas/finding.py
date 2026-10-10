"""Finding and Evidence Schemas."""
from pydantic import BaseModel
from typing import Optional

class FindingResponse(BaseModel):
    id: str
    scan_id: str
    turn_id: str
    category: str
    severity: str
    confidence: float
    description: str
    remediation: Optional[str] = None
