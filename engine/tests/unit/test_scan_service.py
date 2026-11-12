"""Unit tests for ScanService multi-category validation, plan revision, and startup recovery (Task 5 & Task 14).

Tests:
- Rejects unconfirmed authorization.
- Rejects empty category selection.
- Rejects duplicate category IDs.
- Rejects under-development / non-selectable category IDs (e.g. LLM01).
- Rejects mismatched plan revision.
- Accepts valid selectable categories (LLM08).
- Startup recovery marks dangling QUEUED/RUNNING scans as INTERRUPTED.
"""
from datetime import datetime, timezone
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import ScanEntity, ScanTurnEntity, TargetEntity, TargetProfileEntity
from app.schemas.scan import ScanCreate
from app.schemas.target_profile import ReconStageDetail, TargetProfile
from app.agents.planner.rules import TestPlanner
from app.services.scan_service import ScanService


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
            name="Test Target",
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
async def test_start_scan_rejects_unauthorized():
    data = ScanCreate(target_id="tgt-1", category="LLM08", authorized=False)
    with pytest.raises(ValueError, match="authorization"):
        await ScanService.start_scan(data)


@pytest.mark.asyncio
async def test_start_scan_rejects_empty_category_ids():
    data = ScanCreate(target_id="tgt-1", category_ids=[], authorized=True)
    with pytest.raises(ValueError, match="Select at least one category"):
        await ScanService.start_scan(data)


@pytest.mark.asyncio
async def test_start_scan_rejects_duplicate_category_ids():
    data = ScanCreate(target_id="tgt-1", category_ids=["LLM08", "LLM08"], authorized=True)
    with pytest.raises(ValueError, match="Duplicate"):
        await ScanService.start_scan(data)


@pytest.mark.asyncio
async def test_start_scan_rejects_under_development_category(mem_db):
    target_id = str(uuid.uuid4())
    plan = add_target_and_profile(mem_db, target_id)

    # Attempting to scan LLM04 (which is under_development, non-selectable)
    data = ScanCreate(
        target_id=target_id,
        category_ids=["LLM04"],
        plan_revision=plan.plan_revision,
        authorized=True,
    )
    with patch("app.services.scan_service.SessionLocal", mem_db), \
         patch("app.services.target_service.SessionLocal", mem_db), \
         patch("app.services.recon_service.SessionLocal", mem_db):
        with pytest.raises(ValueError, match="under_development|not selectable|unsupported"):
            await ScanService.start_scan(data)


@pytest.mark.asyncio
async def test_start_scan_rejects_mismatched_plan_revision(mem_db):
    target_id = str(uuid.uuid4())
    add_target_and_profile(mem_db, target_id)

    data = ScanCreate(
        target_id=target_id,
        category_ids=["LLM08"],
        plan_revision="stale-revision-12345",
        authorized=True,
    )
    with patch("app.services.scan_service.SessionLocal", mem_db), \
         patch("app.services.target_service.SessionLocal", mem_db), \
         patch("app.services.recon_service.SessionLocal", mem_db):
        with pytest.raises(ValueError, match="revision mismatch|changed"):
            await ScanService.start_scan(data)


@pytest.mark.asyncio
async def test_start_scan_requires_plan_revision(mem_db):
    target_id = str(uuid.uuid4())
    add_target_and_profile(mem_db, target_id)
    data = ScanCreate(target_id=target_id, category_ids=["LLM08"], authorized=True)

    with patch("app.services.scan_service.SessionLocal", mem_db), \
         patch("app.services.target_service.SessionLocal", mem_db), \
         patch("app.services.recon_service.SessionLocal", mem_db):
        with pytest.raises(ValueError, match="plan revision"):
            await ScanService.start_scan(data)


def test_recover_interrupted_scans_marks_dangling_scans(mem_db):
    scan1_id = "dangling-queued-1"
    scan2_id = "dangling-running-2"
    scan3_id = "completed-3"

    with mem_db() as session:
        session.add(ScanEntity(
            id=scan1_id, target_id="tgt-1", status="QUEUED",
            category_results=[{"category": "LLM08", "status": "QUEUED"}],
        ))
        session.add(ScanEntity(
            id=scan2_id, target_id="tgt-1", status="RUNNING",
            category_results=[{"category": "LLM08", "status": "COMPLETED"}, {"category": "LLM09", "status": "RUNNING"}],
        ))
        session.add(ScanEntity(id=scan3_id, target_id="tgt-1", status="COMPLETED"))
        session.commit()

    recovered_count = ScanService.recover_interrupted_scans(session_factory=mem_db)
    assert recovered_count == 2

    with mem_db() as session:
        s1 = session.get(ScanEntity, scan1_id)
        s2 = session.get(ScanEntity, scan2_id)
        s3 = session.get(ScanEntity, scan3_id)
        assert s1.status == "INTERRUPTED"
        assert s1.category_results[0]["status"] == "INTERRUPTED"
        assert s2.status == "INTERRUPTED"
        assert s2.category_results[0]["status"] == "COMPLETED"
        assert s2.category_results[1]["status"] == "INTERRUPTED"
        assert s3.status == "COMPLETED"


@pytest.mark.asyncio
async def test_get_scan_turns_handles_none_response(mem_db):
    target_id = "tgt-1"
    add_target_and_profile(mem_db, target_id)
    scan_id = "scan-null-turn-response"
    with mem_db() as session:
        session.add(ScanEntity(
            id=scan_id,
            target_id=target_id,
            status="COMPLETED",
            category_results=[],
        ))
        session.add(ScanTurnEntity(
            id=str(uuid.uuid4()),
            scan_id=scan_id,
            turn_index=1,
            category="LLM08",
            prompt="Hello",
            response=None,
            latency_ms=10,
            strategy="baseline",
        ))
        session.commit()

    with mem_db() as session:
        assert session.get(ScanEntity, scan_id) is not None

    with patch("app.services.scan_service.SessionLocal", mem_db):
        turns = await ScanService.get_scan_turns(scan_id)
        assert len(turns) == 1
        assert turns[0].response == ""
        assert turns[0].status == "success"
        assert turns[0].verdict is None
