"""Target Registration & Persistence Service."""
import uuid
from typing import List
from app.schemas.target import TargetCreate, TargetResponse, TargetCalibrationConfig

class TargetService:
    _targets = {}

    @classmethod
    async def create_target(cls, data: TargetCreate) -> TargetResponse:
        target_id = str(uuid.uuid4())
        resp = TargetResponse(
            id=target_id,
            name=data.name,
            target_type=data.target_type,
            url=data.url,
            calibration_config=data.calibration_config
        )
        cls._targets[target_id] = resp
        return resp

    @classmethod
    async def list_targets(cls) -> List[TargetResponse]:
        return list(cls._targets.values())

    @classmethod
    async def calibrate_target(cls, target_id: str, config: TargetCalibrationConfig):
        if target_id in cls._targets:
            cls._targets[target_id].calibration_config = config
        return {"status": "calibrated", "target_id": target_id}
