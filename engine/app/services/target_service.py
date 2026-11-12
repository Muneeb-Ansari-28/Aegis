"""Target Registration & Persistence Service."""
import asyncio
import logging
import threading
import uuid
from typing import List, Optional
from app.schemas.target import TargetCreate, TargetResponse, TargetCalibrationConfig, TargetUpdate
from app.core.database import SessionLocal
from app.models.entities import TargetEntity

logger = logging.getLogger(__name__)


class TargetService:
    """
    In-memory target store with validation, lookup, and calibration config updates.
    Will be replaced by SQLAlchemy persistence in a later module.
    """
    _targets: dict[str, TargetResponse] = {}
    _cache_lock = threading.RLock()

    @classmethod
    async def create_target(cls, data: TargetCreate) -> TargetResponse:
        """
        Register a new target after Pydantic validation has passed.

        Args:
            data: Validated TargetCreate payload.

        Returns:
            TargetResponse with generated UUID.
        """
        def _sync() -> TargetResponse:
            target_id = str(uuid.uuid4())
            clean_path = (
                data.project_path.strip()
                if (data.project_path and data.project_path.strip())
                else None
            )
            calibration_dict = (
                data.calibration_config.model_dump(mode="json")
                if hasattr(data.calibration_config, "model_dump")
                else data.calibration_config
                if isinstance(data.calibration_config, dict)
                else None
            )
            with SessionLocal() as session:
                session.add(TargetEntity(
                    id=target_id,
                    name=data.name,
                    target_type=data.target_type,
                    url=data.url,
                    project_path=clean_path,
                    calibration_config=calibration_dict,
                ))
                session.commit()

            resp = TargetResponse(
                id=target_id,
                name=data.name,
                target_type=data.target_type,
                url=data.url,
                project_path=clean_path,
                calibration_config=data.calibration_config,
            )
            with cls._cache_lock:
                cls._targets[target_id] = resp
            return resp

        resp = await asyncio.to_thread(_sync)
        logger.info(f"Registered target '{data.name}' (type={data.target_type}) as {resp.id}")
        return resp

    @classmethod
    async def get_target(cls, target_id: str) -> Optional[TargetResponse]:
        """
        Retrieve a single target by ID from the database, keeping cache synchronized.

        Args:
            target_id: UUID of the target.

        Returns:
            TargetResponse if found, None otherwise.
        """
        def _sync() -> Optional[TargetResponse]:
            with SessionLocal() as session:
                entity = session.get(TargetEntity, target_id)
                if entity is None:
                    with cls._cache_lock:
                        cls._targets.pop(target_id, None)
                    return None
                calibration = (
                    TargetCalibrationConfig.model_validate(entity.calibration_config)
                    if entity.calibration_config else None
                )
                t = TargetResponse(
                    id=entity.id,
                    name=entity.name,
                    target_type=entity.target_type or "web",
                    url=entity.url or "",
                    project_path=entity.project_path,
                    calibration_config=calibration,
                )
                with cls._cache_lock:
                    cls._targets[target_id] = t
                return t

        return await asyncio.to_thread(_sync)

    @classmethod
    async def list_targets(cls) -> List[TargetResponse]:
        """
        Return all registered targets.

        Returns:
            List of TargetResponse instances.
        """
        def _sync() -> List[TargetResponse]:
            targets: List[TargetResponse] = []
            with SessionLocal() as session:
                rows = session.query(TargetEntity).all()
                for entity in rows:
                    calibration = (
                        TargetCalibrationConfig.model_validate(entity.calibration_config)
                        if entity.calibration_config else None
                    )
                    t = TargetResponse(
                        id=entity.id,
                        name=entity.name,
                        target_type=entity.target_type or "web",
                        url=entity.url or "",
                        project_path=entity.project_path,
                        calibration_config=calibration,
                    )
                    with cls._cache_lock:
                        cls._targets[t.id] = t
                    targets.append(t)
            return targets

        return await asyncio.to_thread(_sync)

    @classmethod
    async def update_target(cls, target_id: str, data: TargetUpdate) -> Optional[TargetResponse]:
        """
        Partially update target attributes (such as project_path).
        Distinguishes omitted fields from explicit null/empty updates.
        """
        def _sync() -> Optional[TargetResponse]:
            with SessionLocal() as session:
                entity = session.get(TargetEntity, target_id)
                if entity is None:
                    with cls._cache_lock:
                        cls._targets.pop(target_id, None)
                    return None
                if "project_path" in data.model_fields_set:
                    path_val = (
                        data.project_path.strip()
                        if (data.project_path and data.project_path.strip())
                        else None
                    )
                    entity.project_path = path_val  # type: ignore # pyrefly: ignore[read-only]
                    session.commit()

                calibration = (
                    TargetCalibrationConfig.model_validate(entity.calibration_config)
                    if entity.calibration_config else None
                )
                t = TargetResponse(
                    id=entity.id,
                    name=entity.name,
                    target_type=entity.target_type or "web",
                    url=entity.url or "",
                    project_path=entity.project_path,
                    calibration_config=calibration,
                )
                with cls._cache_lock:
                    cls._targets[target_id] = t
                return t

        return await asyncio.to_thread(_sync)

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
        def _sync() -> Optional[dict]:
            with SessionLocal() as session:
                entity = session.get(TargetEntity, target_id)
                if entity is None:
                    with cls._cache_lock:
                        cls._targets.pop(target_id, None)
                    return None
                entity.calibration_config = config.model_dump(mode="json")  # type: ignore # pyrefly: ignore[read-only]
                session.commit()

                with cls._cache_lock:
                    cls._targets[target_id] = TargetResponse(
                        id=entity.id,
                        name=entity.name,
                        target_type=entity.target_type or "web",
                        url=entity.url or "",
                        project_path=entity.project_path,
                        calibration_config=config,
                    )
            return {"status": "calibrated", "target_id": target_id}

        res = await asyncio.to_thread(_sync)
        if res:
            logger.info(f"Calibrated target {target_id}: input={config.input_selector}")
        return res

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
        def _sync() -> bool:
            with cls._cache_lock:
                in_memory = cls._targets.pop(target_id, None) is not None
            persisted = False
            with SessionLocal() as session:
                entity = session.get(TargetEntity, target_id)
                if entity is not None:
                    session.delete(entity)
                    session.commit()
                    persisted = True
            return in_memory or persisted

        deleted = await asyncio.to_thread(_sync)
        if deleted:
            logger.info(f"Deleted target {target_id}")
        return deleted
