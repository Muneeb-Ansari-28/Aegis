"""Report Data and Metadata Schemas."""
from typing import Dict, List, Optional
from pydantic import BaseModel


class ReportFinding(BaseModel):
    """Individual security finding with correlated turn evidence for reporting."""

    id: str
    category: str
    severity: str
    confidence: float
    description: str
    remediation: Optional[str] = None
    turn_index: int
    prompt: str
    response: str
    latency_ms: Optional[int] = 0
    strategy: Optional[str] = None


class ReportMeta(BaseModel):
    """Metadata regarding a generated PDF assessment report."""

    scan_id: str
    report_path: str
    file_size_bytes: int
    created_at: str
    sha256: Optional[str] = None


class ReportData(BaseModel):
    """Comprehensive structured data feeding executive report generation."""

    scan_id: str
    target_name: str
    target_url: str
    category: str
    scan_status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_turns: int
    total_findings: int
    risk_grade: float
    severity_breakdown: Dict[str, int]
    findings: List[ReportFinding]
    executive_summary: str
    methodology: str
    generated_at: str
