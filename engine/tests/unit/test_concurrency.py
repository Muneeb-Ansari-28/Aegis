"""Concurrency and async safety unit tests (Task 7 & Task 8).

Verifies:
- ScanService start_scan and stop_scan handle concurrent operations safely under lock.
- Targets API interactive calibration cancels running background task on cache eviction.
- Async service methods offload synchronous database work without blocking the event loop.
"""
import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import ScanEntity, TargetEntity, TargetProfileEntity
from app.schemas.scan import ScanCreate
from app.schemas.target_profile import ReconStageDetail, TargetProfile
from app.agents.planner.rules import TestPlanner
from app.services.scan_service import ScanService
from app.services.findings_service import FindingsService
import app.api.v1.targets as targets_api


def complete_profile(target_id: str) -> TargetProfile:
    return TargetProfile(
        target_id=target_id,
        target_url="http://localhost:8000",
        stages={
            "tier1_passive": ReconStageDetail(status="completed"),
            "active_probes": ReconStageDetail(status="completed"),
            "classifier": ReconStageDetail(status="completed"),
        },
    )


def add_target_and_profile(session_factory, target_id: str):
    profile = complete_profile(target_id)
    with session_factory() as session:
        session.add(TargetEntity(
            id=target_id,
            name="Concurrency Target",
            url="http://localhost:8000",
            target_type="web",
            calibration_config={"input_selector": "input", "submit_selector": "button", "response_selector": ".msg"},
        ))
        session.add(TargetProfileEntity(
            id=str(uuid.uuid4()), target_id=target_id, profile_data=profile.model_dump(mode="json")
        ))
        session.commit()
    return TestPlanner.build_test_plan(profile)


@pytest.fixture
def mem_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory
    engine.dispose()


@pytest.mark.asyncio
async def test_scan_service_concurrent_start_and_stop(mem_db):
    """Verify concurrent start and stop do not deadlock, corrupt state, or leak tasks."""
    target_id = str(uuid.uuid4())
    plan = add_target_and_profile(mem_db, target_id)

    run_started = asyncio.Event()
    stop_event = asyncio.Event()

    async def fake_orchestrator_run(*args, **kwargs):
        run_started.set()
        await stop_event.wait()
        return None

    data = ScanCreate(
        target_id=target_id,
        category_ids=["LLM08"],
        plan_revision=plan.plan_revision,
        authorized=True,
        evaluation_oracle={"canary": "TEST-CANARY-1", "known_prompt": "Known test prompt."},
    )

    with patch("app.services.scan_service.SessionLocal", mem_db), \
         patch("app.services.target_service.SessionLocal", mem_db), \
         patch("app.services.recon_service.SessionLocal", mem_db), \
         patch("app.agents.orchestrator.Orchestrator.run", side_effect=fake_orchestrator_run):

        # Start scan
        response = await ScanService.start_scan(data)
        scan_id = response.scan_id
        assert ScanService._orchestrators[scan_id].canary == "TEST-CANARY-1"
        assert ScanService._orchestrators[scan_id].known_prompt == "Known test prompt."

        # Wait until orchestrator is running
        await run_started.wait()

        # Concurrently request stop and query status
        stop_task = asyncio.create_task(ScanService.stop_scan(scan_id))
        status_task = asyncio.create_task(ScanService.get_scan_status(scan_id, session_factory=mem_db))

        stop_res, status_res = await asyncio.gather(stop_task, status_task)

        assert stop_res["status"] == "stop_requested"
        assert status_res.scan_id == scan_id

        # Allow run to complete
        stop_event.set()
        # Give event loop a turn to process finally block in _run_scan
        await asyncio.sleep(0.05)

        async with ScanService._lock:
            assert scan_id not in ScanService._tasks


@pytest.mark.asyncio
async def test_calibration_session_eviction_cancels_active_task():
    """Verify that when registry exceeds capacity, evicted active tasks are cancelled."""
    target_id = str(uuid.uuid4())

    async with targets_api._calibration_lock:
        targets_api._calibration_sessions.clear()
        targets_api._calibration_tasks.clear()

    started_event = asyncio.Event()
    cancelled_event = asyncio.Event()

    async def long_running_calibrate(*args, **kwargs):
        started_event.set()
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            cancelled_event.set()
            raise

    fake_target = TargetEntity(
        id=target_id,
        name="Calib Target",
        url="http://localhost:8000",
        target_type="web",
    )

    with patch.object(targets_api.TargetService, "get_target", new=AsyncMock(return_value=fake_target)), \
         patch("app.api.v1.targets.WebCalibration.calibrate_interactive", side_effect=long_running_calibrate):

        # Start first session (this one will be evicted)
        first_session = await targets_api.interactive_calibrate_target(target_id, timeout_sec=30)
        first_id = first_session.session_id

        first_task = targets_api._calibration_tasks.get(first_id)
        assert first_task is not None
        assert not first_task.done()

        # Ensure first task is actively running calibrate_interactive before evicting
        await started_event.wait()

        # Add 51 more sessions to trigger eviction of the first one
        for i in range(51):
            sess = await targets_api.interactive_calibrate_target(target_id, timeout_sec=30)

        assert first_task.done()

        # Wait briefly for cancellation to propagate
        await asyncio.wait_for(cancelled_event.wait(), timeout=2.0)
        assert cancelled_event.is_set()
        assert first_task.cancelled() or first_task.done()

        async with targets_api._calibration_lock:
            assert first_id not in targets_api._calibration_sessions
            assert first_id not in targets_api._calibration_tasks


@pytest.mark.asyncio
async def test_async_service_db_calls_run_in_worker_thread(mem_db):
    """Verify that synchronous DB work runs in worker threads, not directly on the event loop."""
    import threading

    loop_thread_id = threading.get_ident()
    thread_ids_seen = set()

    scan_id = str(uuid.uuid4())
    with mem_db() as session:
        session.add(ScanEntity(
            id=scan_id,
            target_id="tgt-1",
            status="COMPLETED",
            category="LLM08",
            category_results=[],
        ))
        session.commit()

    def tracking_session_factory():
        thread_ids_seen.add(threading.get_ident())
        return mem_db()

    status = await ScanService.get_scan_status(scan_id, session_factory=tracking_session_factory)
    assert status.scan_id == scan_id

    findings = await FindingsService.get_findings_by_scan(scan_id, session_factory=tracking_session_factory)
    assert findings == []

    # All DB sessions were opened in worker threads, off the event loop thread
    assert len(thread_ids_seen) > 0
    for tid in thread_ids_seen:
        assert tid != loop_thread_id
