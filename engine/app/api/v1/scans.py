"""Scan Lifecycle: Start, Status, and Stop."""
from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.scan import ScanCreate, ScanResponse, ScanStatusResponse
from app.services.scan_service import ScanService

router = APIRouter()

@router.post("/start", response_model=ScanResponse)
async def start_scan(payload: ScanCreate):
    return await ScanService.start_scan(payload)

@router.get("/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: str):
    return await ScanService.get_scan_status(scan_id)

@router.post("/{scan_id}/stop")
async def stop_scan(scan_id: str):
    return await ScanService.stop_scan(scan_id)
