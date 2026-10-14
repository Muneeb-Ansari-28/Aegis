"""Target Registration & Persistence Service."""
import logging
import uuid
from typing import List, Optional
from app.schemas.target import TargetCreate, TargetResponse, TargetCalibrationConfig
from app.core.database import SessionLocal
from app.models.entities import TargetEntity

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
        with SessionLocal() as session:
            session.add(TargetEntity(
                id=target_id,
                name=data.name,
                target_type=data.target_type,
                url=data.url,
                calibration_config=(
                    data.calibration_config.model_dump(mode="json")
                    if data.calibration_config else None
                ),
            ))
            session.commit()
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
        target = cls._targets.get(target_id)
        if target is not None:
            return target
        with SessionLocal() as session:
            entity = session.get(TargetEntity, target_id)
        if entity is None:
            return None
        calibration = (
            TargetCalibrationConfig.model_validate(entity.calibration_config)
            if entity.calibration_config else None
        )
        target = TargetResponse(
            id=entity.id,
            name=entity.name,
            target_type=entity.target_type,
            url=entity.url,
            calibration_config=calibration,
        )
        cls._targets[target_id] = target
        return target

    @classmethod
    async def list_targets(cls) -> List[TargetResponse]:
        """
        Return all registered targets.

        Returns:
            List of TargetResponse instances.
        """
        with SessionLocal() as session:
            rows = session.query(TargetEntity).all()
        targets: List[TargetResponse] = []
        for entity in rows:
            calibration = (
                TargetCalibrationConfig.model_validate(entity.calibration_config)
                if entity.calibration_config else None
            )
            target = TargetResponse(
                id=entity.id,
                name=entity.name,
                target_type=entity.target_type,
                url=entity.url,
                calibration_config=calibration,
            )
            cls._targets[target.id] = target
            targets.append(target)
        return targets

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
        with SessionLocal() as session:
            entity = session.get(TargetEntity, target_id)
            if entity:
                entity.calibration_config = config.model_dump(mode="json")
                session.commit()
        logger.info(f"Calibrated target {target_id}: input={config.input_selector}")
        return {"status": "calibrated", "target_id": target_id}

    @classmethod
    async def delete_target(cls, target_id: str) -> bool:
        """
        Remove a target from the in-memory store and the database.

        The in-memory cache alone is not authoritative: ``list_targets`` reads
        the persisted rows, so a cache-only delete would reappear immediately.

        Args:
            target_id: UUID of the target.

        Returns:
            True if the target was removed from either store, False if not found.
        """
        in_memory = cls._targets.pop(target_id, None) is not None
        persisted = False
        with SessionLocal() as session:
            entity = session.get(TargetEntity, target_id)
            if entity is not None:
                session.delete(entity)
                session.commit()
                persisted = True
        deleted = in_memory or persisted
        if deleted:
            logger.info(f"Deleted target {target_id}")
        return deleted
