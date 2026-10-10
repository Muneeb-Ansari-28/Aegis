"""Target Registration & Calibration Endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.target import TargetCreate, TargetResponse, TargetCalibrationConfig
from app.services.target_service import TargetService

router = APIRouter()

@router.post("", response_model=TargetResponse)
async def register_target(payload: TargetCreate):
    return await TargetService.create_target(payload)

@router.get("", response_model=List[TargetResponse])
async def list_targets():
    return await TargetService.list_targets()

@router.post("/{target_id}/calibrate")
async def calibrate_target(target_id: str, config: TargetCalibrationConfig):
    return await TargetService.calibrate_target(target_id, config)
