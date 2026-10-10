"""Scan Lifecycle Request/Response Schemas."""
from pydantic import BaseModel
from typing import Optional

class ScanCreate(BaseModel):
    target_id: str
    category: str = "LLM07"
    budget: int = 10

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

