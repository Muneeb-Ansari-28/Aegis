"""Judge Verdict JSON Contract."""
from pydantic import BaseModel, Field
from typing import List, Optional

class JudgeVerdict(BaseModel):
    """Evaluation result including deterministic system-prompt disclosure evidence."""
    exploited: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    indicators_found: List[str] = Field(default_factory=list)
    canary_detected: bool = False
    overlap_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    category: str = "LLM08"
