"""Target Registration & Calibration Endpoints."""
import asyncio
import uuid
from typing import Dict
from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.target import (
    CalibrationSessionResponse,
    TargetCreate,
    TargetResponse,
    TargetCalibrationConfig,
)
from app.services.target_service import TargetService
from app.adapters.web_calibration import WebCalibration

router = APIRouter()
_calibration_sessions: Dict[str, CalibrationSessionResponse] = {}
_calibration_tasks: Dict[str, asyncio.Task[None]] = {}


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


@router.post("/{target_id}/calibrate/auto")
async def auto_calibrate_target(target_id: str) -> dict:
    """Detect a web chat interface with the existing Playwright calibration module."""
    target = await TargetService.get_target(target_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found.")
    if target.target_type != "web":
        raise HTTPException(status_code=400, detail="Playwright calibration supports web targets only.")
    try:
        config = await WebCalibration().auto_calibrate(target.url, headless=False)
    except Exception as exc:
        detail = str(exc) or type(exc).__name__
        raise HTTPException(
            status_code=502,
            detail=f"Playwright auto-calibration failed: {detail}",
        ) from exc
    await TargetService.calibrate_target(target_id, config)
    return {"status": "calibrated", "target_id": target_id, "calibration_config": config.model_dump()}


@router.post(
    "/{target_id}/calibrate/interactive",
    response_model=CalibrationSessionResponse,
    status_code=202,
)
async def interactive_calibrate_target(
    target_id: str, timeout_sec: int = 90
) -> CalibrationSessionResponse:
    """Start visible calibration and return an ID the desktop can poll for clicks."""
    target = await TargetService.get_target(target_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found.")
    if target.target_type != "web":
        raise HTTPException(status_code=400, detail="Playwright calibration supports web targets only.")
    if timeout_sec < 15 or timeout_sec > 180:
        raise HTTPException(status_code=422, detail="timeout_sec must be between 15 and 180.")
    session_id = str(uuid.uuid4())
    session = CalibrationSessionResponse(
        session_id=session_id,
        target_id=target_id,
        status="opening_browser",
        step=0,
    )
    _calibration_sessions[session_id] = session
    while len(_calibration_sessions) > 50:
        expired_id = next(iter(_calibration_sessions))
        _calibration_sessions.pop(expired_id, None)
        _calibration_tasks.pop(expired_id, None)
    _calibration_tasks[session_id] = asyncio.create_task(
        _run_interactive_calibration(session_id, target.url, timeout_sec)
    )
    return session


async def _run_interactive_calibration(
    session_id: str, target_url: str, timeout_sec: int
) -> None:
    """Run browser capture and publish each selected control to the session record."""
    session = _calibration_sessions[session_id]

    async def update_progress(step: int) -> None:
        session.step = step
        session.input_selected = step >= 1
        session.enter_selected = step >= 2
        # Step 2 means both controls were captured, not that the session is
        # finished. The status stays "saving_selectors" until the response area
        # is detected and calibration_config is persisted, so clients never see
        # status="completed" while calibration_config is still unset.
        session.status = "saving_selectors" if step >= 2 else "capturing_controls"

    try:
        config = await WebCalibration().calibrate_interactive(
            target_url,
            timeout_sec=timeout_sec,
            progress_callback=update_progress,
        )
        await TargetService.calibrate_target(session.target_id, config)
        session.calibration_config = config
        session.status = "completed"
    except Exception as exc:
        session.status = "failed"
        session.error = str(exc) or type(exc).__name__
    finally:
        _calibration_tasks.pop(session_id, None)


@router.get(
    "/{target_id}/calibrate/interactive/{session_id}",
    response_model=CalibrationSessionResponse,
)
async def get_interactive_calibration_status(
    target_id: str, session_id: str
) -> CalibrationSessionResponse:
    """Return click checklist progress for an active or completed calibration."""
    session = _calibration_sessions.get(session_id)
    if session is None or session.target_id != target_id:
        raise HTTPException(status_code=404, detail="Calibration session not found.")
    return session


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
