"""Findings and Evidence Inspection Endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException

from app.schemas.finding import FindingDetail, FindingResponse, FindingsSummary
from app.services.findings_service import FindingsService

router = APIRouter()


@router.get("/detail/{finding_id}", response_model=FindingDetail)
async def get_finding_detail(finding_id: str) -> FindingDetail:
    """
    Retrieve finding detail including linked prompt/response turn evidence.

    Args:
        finding_id: The UUID of the finding to inspect.

    Returns:
        FindingDetail with full evidence.

    Raises:
        HTTPException: 404 if finding or linked turn is not found.
    """
    try:
        return await FindingsService.get_finding_detail(finding_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{scan_id}", response_model=List[FindingResponse])
async def get_findings_by_scan(scan_id: str) -> List[FindingResponse]:
    """
    Retrieve all findings for a scan ordered by creation time.

    Args:
        scan_id: The UUID of the scan.

    Returns:
        List of FindingResponse models.

    Raises:
        HTTPException: 404 if scan is not found.
    """
    try:
        return await FindingsService.get_findings_by_scan(scan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{scan_id}/summary", response_model=FindingsSummary)
async def get_findings_summary(scan_id: str) -> FindingsSummary:
    """
    Retrieve finding summary counts by severity and overall risk grade.

    Args:
        scan_id: The UUID of the scan.

    Returns:
        FindingsSummary with aggregate risk metrics.

    Raises:
        HTTPException: 404 if scan is not found.
    """
    try:
        return await FindingsService.get_findings_summary(scan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
