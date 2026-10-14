"""Scan Lifecycle: Start, Status, and Stop."""
from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.scan import ScanCreate, ScanResponse, ScanStatusResponse, ScanTurnResponse
from app.services.scan_service import ScanService

router = APIRouter()

@router.post("/start", response_model=ScanResponse)
async def start_scan(payload: ScanCreate):
    try:
        return await ScanService.start_scan(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: str):
    try:
        return await ScanService.get_scan_status(scan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/{scan_id}/turns", response_model=List[ScanTurnResponse])
async def get_scan_turns(scan_id: str):
    """Replay persisted prompt/response turns for the live chat view."""
    try:
        return await ScanService.get_scan_turns(scan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/{scan_id}/stop")
async def stop_scan(scan_id: str):
    try:
        return await ScanService.stop_scan(scan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
