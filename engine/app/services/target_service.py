"""Target Registration & Persistence Service."""
import logging
import uuid
from typing import List, Optional
from app.schemas.target import TargetCreate, TargetResponse, TargetCalibrationConfig

logger = logging.getLogger(__name__)


class TargetService:
    """
    In-memory target store with validation, lookup, and calibration config updates.
    Will be replaced by SQLAlchemy persistence in a later module.
    """
    _targets: dict[str, TargetResponse] = {}

    @classmethod
    async def create_target(cls, data: TargetCreate) -> TargetResponse:
        """
        Register a new target after Pydantic validation has passed.

        Args:
            data: Validated TargetCreate payload.

        Returns:
            TargetResponse with generated UUID.
        """
        target_id = str(uuid.uuid4())
        resp = TargetResponse(
            id=target_id,
            name=data.name,
            target_type=data.target_type,
            url=data.url,
            calibration_config=data.calibration_config,
        )
        cls._targets[target_id] = resp
        logger.info(f"Registered target '{data.name}' (type={data.target_type}) as {target_id}")
        return resp

    @classmethod
    async def get_target(cls, target_id: str) -> Optional[TargetResponse]:
        """
        Retrieve a single target by ID.

        Args:
            target_id: UUID of the target.

        Returns:
            TargetResponse if found, None otherwise.
        """
        return cls._targets.get(target_id)

    @classmethod
    async def list_targets(cls) -> List[TargetResponse]:
        """
        Return all registered targets.

        Returns:
            List of TargetResponse instances.
        """
        return list(cls._targets.values())

    @classmethod
    async def calibrate_target(
        cls, target_id: str, config: TargetCalibrationConfig
    ) -> Optional[dict]:
        """
        Update calibration selectors for an existing target.

        Args:
            target_id: UUID of the target.
            config: New calibration selectors.

        Returns:
            Status dict if target exists, None if target not found.
        """
        target = cls._targets.get(target_id)
        if target is None:
            return None
        target.calibration_config = config
        logger.info(f"Calibrated target {target_id}: input={config.input_selector}")
        return {"status": "calibrated", "target_id": target_id}

    @classmethod
    async def delete_target(cls, target_id: str) -> bool:
        """
        Remove a target from the store.

        Args:
            target_id: UUID of the target.

        Returns:
            True if deleted, False if not found.
        """
        if target_id in cls._targets:
            del cls._targets[target_id]
            logger.info(f"Deleted target {target_id}")
            return True
        return False
