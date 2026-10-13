"""Target Registration & Calibration Endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.target import TargetCreate, TargetResponse, TargetCalibrationConfig
from app.services.target_service import TargetService

router = APIRouter()


@router.post("", response_model=TargetResponse, status_code=201)
async def register_target(payload: TargetCreate) -> TargetResponse:
    """
    Register a new scan target.

    Validates name (non-empty, max 200), url (http/https), and target_type (web/api/app).
    Returns 422 for invalid input via Pydantic validators.
    """
    return await TargetService.create_target(payload)


@router.get("", response_model=List[TargetResponse])
async def list_targets() -> List[TargetResponse]:
    """List all registered targets."""
    return await TargetService.list_targets()


@router.get("/{target_id}", response_model=TargetResponse)
async def get_target(target_id: str) -> TargetResponse:
    """
    Retrieve a single target by UUID.

    Raises:
        HTTPException 404 if target_id is not found.
    """
    target = await TargetService.get_target(target_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found.")
    return target


@router.post("/{target_id}/calibrate")
async def calibrate_target(target_id: str, config: TargetCalibrationConfig) -> dict:
    """
    Update the calibration CSS selectors for a target.

    Raises:
        HTTPException 404 if target_id is not found.
    """
    result = await TargetService.calibrate_target(target_id, config)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found.")
    return result


@router.delete("/{target_id}", status_code=204)
async def delete_target(target_id: str) -> None:
    """
    Remove a registered target.

    Raises:
        HTTPException 404 if target_id is not found.
    """
    deleted = await TargetService.delete_target(target_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found.")
