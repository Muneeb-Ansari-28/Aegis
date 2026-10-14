"""Scan lifecycle service that dispatches authorized local web scans."""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List
import uuid

from app.adapters.playwright_web import PlaywrightWebAdapter
from app.agents.orchestrator import Orchestrator
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.events import event_bus
from app.models.entities import FindingEntity, ScanEntity, ScanTurnEntity
from app.schemas.scan import ScanCreate, ScanResponse, ScanStatusResponse, ScanTurnResponse
from app.services.target_service import TargetService

logger = logging.getLogger(__name__)


class ScanService:
    """Start, inspect, and stop in-process scan orchestrations."""

    _scans: Dict[str, ScanResponse] = {}
    _orchestrators: Dict[str, Orchestrator] = {}
    _tasks: Dict[str, asyncio.Task[None]] = {}
    _exploited: Dict[str, bool] = {}

    @classmethod
    async def start_scan(cls, data: ScanCreate) -> ScanResponse:
        """Validate an authorized local target and dispatch its visible Playwright scan."""
        if not data.authorized:
            raise ValueError("Confirm authorization before starting a scan.")
        if data.category != "LLM07":
            raise ValueError("The active scan pipeline currently supports OWASP LLM07 only.")
        if data.budget > get_settings().MAX_ATTEMPTS_PER_CATEGORY:
            raise ValueError(
                f"Prompt budget cannot exceed {get_settings().MAX_ATTEMPTS_PER_CATEGORY}."
            )

        target = await TargetService.get_target(data.target_id)
        if target is None:
            raise LookupError("The selected target was not found.")
        if target.target_type != "web":
            raise ValueError("The Playwright scan pipeline supports web targets only.")
        if target.calibration_config is None:
            raise ValueError("Calibrate the target before starting a scan.")

        scan_id = str(uuid.uuid4())
        response = ScanResponse(
            scan_id=scan_id,
            target_id=target.id,
            status="QUEUED",
            category=data.category,
            budget=data.budget,
        )
        adapter = PlaywrightWebAdapter(
            target_url=target.url,
            selectors=target.calibration_config,
            headless=False,
        )
        orchestrator = Orchestrator(
            scan_id=scan_id,
            adapter=adapter,
            max_budget=data.budget,
        )
        with SessionLocal() as session:
            session.add(ScanEntity(
                id=scan_id,
                target_id=target.id,
                status="QUEUED",
                category=data.category,
                budget=data.budget,
            ))
            session.commit()

        cls._scans[scan_id] = response
        cls._orchestrators[scan_id] = orchestrator
        cls._exploited[scan_id] = False
        await event_bus.publish(scan_id, {
            "scan_id": scan_id,
            "event": "scan_queued",
            "status": "QUEUED",
            "category": data.category,
            "budget": data.budget,
        })
        cls._tasks[scan_id] = asyncio.create_task(cls._run_scan(scan_id, orchestrator))
        return response

    @classmethod
    async def _run_scan(cls, scan_id: str, orchestrator: Orchestrator) -> None:
        """Run an orchestrator, update its persisted lifecycle state, and retain outcome."""
        try:
            verdict = await orchestrator.run()
            cls._exploited[scan_id] = bool(verdict and verdict.exploited)
        except Exception:
            logger.exception("Scan %s failed", scan_id)
        finally:
            response = cls._scans[scan_id]
            response.status = orchestrator.state.value
            with SessionLocal() as session:
                entity = session.get(ScanEntity, scan_id)
                if entity:
                    entity.status = orchestrator.state.value
                    entity.current_attempt = orchestrator.current_attempt
                    if orchestrator.state.value in {"COMPLETED", "STOPPED", "FAILED"}:
                        entity.completed_at = datetime.utcnow()
                    session.commit()
            cls._tasks.pop(scan_id, None)

    @classmethod
    async def get_scan_status(
        cls, scan_id: str, session_factory=SessionLocal
    ) -> ScanStatusResponse:
        """
        Return current orchestrator state and attempt counts for a scan.

        When the orchestrator is no longer in memory (for example after an
        engine restart), the persisted scan row is used so completed scans
        keep answering status and turn requests.
        """
        response = cls._scans.get(scan_id)
        orchestrator = cls._orchestrators.get(scan_id)
        if response is not None and orchestrator is not None:
            return ScanStatusResponse(
                scan_id=scan_id,
                status=orchestrator.state.value,
                current_attempt=orchestrator.current_attempt,
                budget=response.budget,
                exploited=cls._exploited.get(scan_id, False),
            )
        with session_factory() as session:
            entity = session.get(ScanEntity, scan_id)
            if entity is None:
                raise LookupError(f"Scan '{scan_id}' was not found.")
            exploited = (
                session.query(FindingEntity)
                .filter(FindingEntity.scan_id == scan_id)
                .first()
                is not None
            )
            return ScanStatusResponse(
                scan_id=scan_id,
                status=entity.status,
                current_attempt=entity.current_attempt,
                budget=entity.budget,
                exploited=exploited,
            )

    @classmethod
    async def get_scan_turns(
        cls, scan_id: str, session_factory=SessionLocal
    ) -> List[ScanTurnResponse]:
        """
        Return persisted turns for a scan ordered by turn index.

        Args:
            scan_id: UUID of the scan.
            session_factory: Injectable SQLAlchemy session factory.

        Returns:
            List of ScanTurnResponse rows; empty when no turn was persisted.

        Raises:
            LookupError: When the scan does not exist.
        """
        with session_factory() as session:
            if session.get(ScanEntity, scan_id) is None:
                raise LookupError(f"Scan '{scan_id}' was not found.")
            rows = (
                session.query(ScanTurnEntity)
                .filter(ScanTurnEntity.scan_id == scan_id)
                .order_by(ScanTurnEntity.turn_index)
                .all()
            )
            return [
                ScanTurnResponse(
                    turn_index=row.turn_index,
                    prompt=row.prompt,
                    response=row.response,
                    latency_ms=row.latency_ms or 0,
                    strategy=row.strategy,
                    verdict=row.verdict,
                    created_at=(
                        row.created_at.isoformat() if row.created_at else None
                    ),
                )
                for row in rows
            ]

    @classmethod
    async def stop_scan(cls, scan_id: str) -> Dict[str, str]:
        """Request that a running scan stop at the next turn boundary."""
        orchestrator = cls._orchestrators.get(scan_id)
        if orchestrator is None:
            raise LookupError(f"Scan '{scan_id}' was not found in this engine session.")
        if scan_id in cls._tasks:
            orchestrator.stop()
            return {"status": "stop_requested", "scan_id": scan_id}
        return {"status": orchestrator.state.value.lower(), "scan_id": scan_id}
