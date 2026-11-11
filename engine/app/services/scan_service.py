"""Scan lifecycle service that dispatches authorized local web scans."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from app.adapters.playwright_web import PlaywrightWebAdapter
from app.agents.orchestrator import Orchestrator
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.events import event_bus
from app.models.entities import FindingEntity, ScanEntity, ScanTurnEntity
from app.schemas.scan import CategoryRunStatus, ScanCreate, ScanResponse, ScanStatusResponse, ScanTurnResponse
from app.schemas.target_profile import TargetProfile
from app.services.target_service import TargetService

logger = logging.getLogger(__name__)


class ScanService:
    """Start, inspect, and stop in-process scan orchestrations."""

    _scans: Dict[str, ScanResponse] = {}
    _orchestrators: Dict[str, Orchestrator] = {}
    _tasks: Dict[str, asyncio.Task[None]] = {}
    _exploited: Dict[str, bool] = {}

    SUPPORTED_CATEGORIES = {
        "LLM01", "LLM02", "LLM03", "LLM04", "LLM05",
        "LLM06", "LLM07", "LLM08", "LLM09", "LLM10"
    }

    @classmethod
    async def start_scan(cls, data: ScanCreate) -> ScanResponse:
        """Validate an authorized local target and dispatch its visible Playwright scan."""
        if not data.authorized:
            raise ValueError("Confirm authorization before starting a scan.")

        category_ids = data.category_ids
        if not category_ids:
            raise ValueError("Select at least one category to scan.")

        normalized_cats = [c.upper() for c in category_ids]
        if len(normalized_cats) != len(set(normalized_cats)):
            raise ValueError("Duplicate category IDs provided in scan request.")

        for cat in normalized_cats:
            if cat not in cls.SUPPORTED_CATEGORIES:
                raise ValueError(
                    f"OWASP category '{cat}' is not recognized. "
                    f"Choose from: {', '.join(sorted(cls.SUPPORTED_CATEGORIES))}."
                )

        if data.budget > get_settings().MAX_ATTEMPTS_PER_CATEGORY:
            raise ValueError(
                f"Prompt budget cannot exceed {get_settings().MAX_ATTEMPTS_PER_CATEGORY}."
            )

        target = await TargetService.get_target(data.target_id)
        if target is None:
            raise LookupError("The selected target was not found.")
        if target.target_type != "web":
            raise ValueError("The Playwright scan pipeline supports web targets only.")
        if not target.url:
            raise ValueError("Target URL is required for web scanning.")
        if target.calibration_config is None:
            raise ValueError("Calibrate the target before starting a scan.")

        if not data.plan_revision:
            raise ValueError("A current test plan revision is required. Run recon and review the plan before scanning.")

        # Retrieve the latest recon profile and generate the authoritative plan.
        from app.services.recon_service import ReconService
        from app.agents.planner.rules import TestPlanner
        profile = ReconService.get_target_profile(target.id, session_factory=SessionLocal)
        if profile is None:
            raise ValueError("Recon has not produced a target profile. Run recon before starting a scan.")
        test_plan = TestPlanner.build_test_plan(profile)
        if not test_plan.is_complete:
            raise ValueError("Recon or planning is incomplete. Complete the required recon stages before scanning.")

        # A plan revision is mandatory and is always checked against the current profile.
        if test_plan.plan_revision != data.plan_revision:
            raise ValueError(
                f"Plan revision mismatch: The test plan has changed "
                f"(current: {test_plan.plan_revision[:8]}, requested: {data.plan_revision[:8]}). "
                f"Please refresh and review the plan."
            )

        # Revalidate every requested category against the plan's selectable_category_ids
        for cat_id in normalized_cats:
            if cat_id not in test_plan.selectable_category_ids:
                cat_def = next((c for c in test_plan.categories if c.category == cat_id), None)
                status_str = cat_def.implementation_status if cat_def else "unknown"
                reason_str = cat_def.reason if cat_def else "Category not ready for automated scanning"
                raise ValueError(
                    f"Category '{cat_id}' is not selectable in the current test plan (status: {status_str}, reason: {reason_str}). "
                    f"Only ready categories can be scanned: {', '.join(test_plan.selectable_category_ids)}."
                )

        primary_cat = normalized_cats[0]
        selected_plans = [
            item.model_copy(update={"budget": data.budget})
            for item in test_plan.categories
            if item.category in normalized_cats
        ]
        scan_id = str(uuid.uuid4())
        total_budget = data.budget * len(selected_plans)
        initial_results = [
            CategoryRunStatus(
                category=item.category,
                name=item.name,
                status="QUEUED",
                attempts=0,
                budget=item.budget,
                exploited=False,
            )
            for item in selected_plans
        ]
        response = ScanResponse(
            scan_id=scan_id,
            target_id=target.id,
            status="QUEUED",
            category=primary_cat,
            category_ids=normalized_cats,
            budget=total_budget,
            plan_revision=test_plan.plan_revision,
            category_results=initial_results,
        )

        def adapter_factory() -> PlaywrightWebAdapter:
            return PlaywrightWebAdapter(
                target_url=target.url,
                selectors=target.calibration_config,
                headless=False,
            )

        def persist_category_results(results: List[dict]) -> None:
            response.category_results = [CategoryRunStatus.model_validate(item) for item in results]
            with SessionLocal() as session:
                entity = session.get(ScanEntity, scan_id)
                if entity is not None:
                    entity.category_results = results  # type: ignore # pyrefly: ignore[read-only]
                    session.commit()

        orchestrator = Orchestrator(
            scan_id=scan_id,
            adapter_factory=adapter_factory,
            category_plans=selected_plans,
            category_update_callback=persist_category_results,
        )

        with SessionLocal() as session:
            session.add(ScanEntity(
                id=scan_id,
                target_id=target.id,
                status="QUEUED",
                category=",".join(normalized_cats),
                budget=total_budget,
                test_plan=test_plan.model_dump(mode="json") if test_plan else None,
                category_results=[item.model_dump(mode="json") for item in initial_results],
            ))
            session.commit()

        cls._scans[scan_id] = response
        cls._orchestrators[scan_id] = orchestrator
        cls._exploited[scan_id] = False
        await event_bus.publish(scan_id, {
            "scan_id": scan_id,
            "event": "scan_queued",
            "status": "QUEUED",
            "category": primary_cat,
            "category_ids": normalized_cats,
            "budget": total_budget,
            "category_results": [item.model_dump(mode="json") for item in initial_results],
        })
        cls._tasks[scan_id] = asyncio.create_task(cls._run_scan(scan_id, orchestrator))
        return response

    @classmethod
    async def _run_scan(cls, scan_id: str, orchestrator: Orchestrator) -> None:
        """Run an orchestrator, update its persisted lifecycle state, and retain outcome."""
        try:
            with SessionLocal() as session:
                entity = session.get(ScanEntity, scan_id)
                if entity is not None:
                    entity.status = "RUNNING"  # type: ignore # pyrefly: ignore[read-only]
                    session.commit()

            if scan_id in cls._scans:
                cls._scans[scan_id].status = "RUNNING"

            verdict = await orchestrator.run()
            cls._exploited[scan_id] = bool(verdict and verdict.exploited)
        except Exception:
            logger.exception("Scan %s failed", scan_id)
        finally:
            response = cls._scans.get(scan_id)
            if response:
                response.status = orchestrator.state.value
                response.category_results = [
                    CategoryRunStatus.model_validate(item)
                    for item in orchestrator.category_results
                ]
            with SessionLocal() as session:
                entity = session.get(ScanEntity, scan_id)
                if entity is not None:
                    entity.status = orchestrator.state.value  # type: ignore # pyrefly: ignore[read-only]
                    entity.current_attempt = orchestrator.current_attempt  # type: ignore # pyrefly: ignore[read-only]
                    entity.category_results = orchestrator.category_results  # type: ignore # pyrefly: ignore[read-only]
                    if orchestrator.state.value in {"COMPLETED", "PARTIAL", "STOPPED", "FAILED"}:
                        entity.completed_at = datetime.now(timezone.utc)  # type: ignore # pyrefly: ignore[read-only]
                    session.commit()
            cls._tasks.pop(scan_id, None)

    @classmethod
    def recover_interrupted_scans(cls, session_factory=SessionLocal) -> int:
        """
        On engine startup, identify previously queued/running scans whose
        in-process task no longer exists and mark them INTERRUPTED.
        """
        with session_factory() as session:
            dangling = (
                session.query(ScanEntity)
                .filter(ScanEntity.status.in_(["QUEUED", "RUNNING"]))
                .all()
            )
            count = len(dangling)
            for scan in dangling:
                scan.status = "INTERRUPTED"  # type: ignore # pyrefly: ignore[read-only]
                scan.completed_at = datetime.now(timezone.utc)  # type: ignore # pyrefly: ignore[read-only]
                scan.category_results = [  # type: ignore # pyrefly: ignore[read-only]
                    {
                        **result,
                        **(
                            {
                                "status": "INTERRUPTED",
                                "error": "Engine restarted before this category completed.",
                            }
                            if result.get("status") in {"QUEUED", "RUNNING"}
                            else {}
                        ),
                    }
                    for result in (scan.category_results or [])
                ]
            session.commit()
            if count > 0:
                logger.info(f"Recovered {count} interrupted scan(s) to INTERRUPTED state.")
            return count

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
                category=response.category,
                category_ids=response.category_ids,
                current_attempt=orchestrator.current_attempt,
                budget=response.budget,
                exploited=cls._exploited.get(scan_id, False),
                category_results=response.category_results,
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
            cat_raw = getattr(entity, "category", "LLM08") or "LLM08"
            cat_list = [c.strip() for c in cat_raw.split(",") if c.strip()]
            return ScanStatusResponse(
                scan_id=scan_id,
                status=entity.status,
                category=cat_list[0] if cat_list else "LLM08",
                category_ids=cat_list,
                current_attempt=entity.current_attempt,
                budget=entity.budget,
                exploited=exploited,
                category_results=[
                    CategoryRunStatus.model_validate(item)
                    for item in (entity.category_results or [])
                ],
            )

    @classmethod
    async def get_scan_turns(
        cls, scan_id: str, session_factory=SessionLocal
    ) -> List[ScanTurnResponse]:
        """
        Return persisted turns for a scan ordered by turn index.
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
                    category=row.category,
                    prompt=row.prompt,
                    response=row.response,
                    status=("timeout" if row.response.startswith("[CONNECTOR_TIMEOUT]")
                            else "error" if row.response.startswith("[CONNECTOR_ERROR]")
                            else "success"),
                    latency_ms=row.latency_ms or 0,
                    strategy=row.strategy,
                    verdict=None if row.response.startswith(("[CONNECTOR_ERROR]", "[CONNECTOR_TIMEOUT]")) else row.verdict,
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
