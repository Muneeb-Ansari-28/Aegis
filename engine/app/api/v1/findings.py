"""Findings and Evidence Inspection Endpoints."""
from fastapi import APIRouter
from typing import List
from app.schemas.finding import FindingResponse

router = APIRouter()

@router.get("/{scan_id}", response_model=List[FindingResponse])
async def get_findings_by_scan(scan_id: str):
    return []
