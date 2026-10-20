"""Integration tests for end-to-end findings persistence against weak-bot target."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import threading
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uvicorn

from app.adapters.playwright_web import PlaywrightWebAdapter
from app.agents.orchestrator import Orchestrator
from app.core.database import Base
from app.models.entities import FindingEntity, ScanEntity, TargetEntity
from app.services.findings_service import FindingsService


import socket

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def weak_bot_server():
    """Starts local weak-bot server in background thread on dynamic free port."""
    port = find_free_port()
    weak_bot_path = Path(__file__).resolve().parents[3] / "test-targets" / "weak-bot" / "app.py"
    spec = importlib.util.spec_from_file_location("weak_bot_app", str(weak_bot_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    server_thread = threading.Thread(
        target=lambda: uvicorn.run(mod.app, host="127.0.0.1", port=port, log_level="warning"),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.5)
    yield f"http://127.0.0.1:{port}"


@pytest.fixture
def test_db_session():
    """Create in-memory SQLite database session factory for persistence tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


@pytest.mark.asyncio
async def test_findings_persistence_weak_bot(weak_bot_server, test_db_session):
    """
    Execute full scan against live weak-bot, assert finding is persisted to SQLite,
    and verify findings service retrieves exact evidence.
    """
    scan_id = "test-scan-weak-bot-persistence"
    target_id = "test-target-weak-bot"

    # 1. Seed target and scan records
    with test_db_session() as session:
        target = TargetEntity(
            id=target_id,
            name="Weak Bot Test Target",
            target_type="web",
            url=weak_bot_server,
            created_at=datetime.now(timezone.utc),
        )
        session.add(target)

        scan = ScanEntity(
            id=scan_id,
            target_id=target_id,
            status="QUEUED",
            category="LLM07",
            budget=3,
            current_attempt=0,
            created_at=datetime.now(timezone.utc),
        )
        session.add(scan)
        session.commit()

    # 2. Run orchestrator with headless PlaywrightWebAdapter
    adapter = PlaywrightWebAdapter(target_url=weak_bot_server, headless=True)
    orchestrator = Orchestrator(
        scan_id=scan_id,
        adapter=adapter,
        max_budget=3,
        session_factory=test_db_session,
    )

    verdict = await orchestrator.run()

    # 3. Assert scan finished with confirmed exploit
    assert verdict is not None
    assert verdict.exploited is True
    assert "canary" in verdict.rationale.lower() or "canary" in str(verdict.indicators_found).lower()

    # 4. Verify findings persisted directly in SQLite
    with test_db_session() as session:
        finding_rows = session.query(FindingEntity).filter(FindingEntity.scan_id == scan_id).all()
        assert len(finding_rows) >= 1
        db_finding = finding_rows[0]
        assert db_finding.category == "LLM07"
        assert db_finding.severity in ("CRITICAL", "HIGH")
        assert db_finding.confidence == 1.0

    # 5. Verify FindingsService returns matching structured data
    findings = await FindingsService.get_findings_by_scan(scan_id, session_factory=test_db_session)
    assert len(findings) >= 1
    assert findings[0].scan_id == scan_id
    assert findings[0].category == "LLM07"
    assert findings[0].severity in ("CRITICAL", "HIGH")

    # 6. Verify FindingDetail correlates with the trigger prompt and response
    detail = await FindingsService.get_finding_detail(findings[0].id, session_factory=test_db_session)
    assert detail.id == findings[0].id
    assert detail.turn_index >= 1
    assert "AEGIS-CANARY-7731" in detail.response
    assert len(detail.prompt) > 0
    assert detail.remediation is not None
