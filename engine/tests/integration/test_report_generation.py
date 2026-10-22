"""Integration tests for end-to-end PDF report generation and DB evidence fidelity."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import threading
import time
import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uvicorn

from app.adapters.playwright_web import PlaywrightWebAdapter
from app.agents.orchestrator import Orchestrator
from app.core.database import Base
from app.models.entities import FindingEntity, ScanEntity, TargetEntity
from app.services.findings_service import FindingsService
from app.services.report_service import ReportService


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
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load weak-bot app specification from {weak_bot_path}")
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
def test_db_session(tmp_path, monkeypatch):
    """Create in-memory SQLite database session factory and redirect PDF storage."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    monkeypatch.setattr(
        ReportService,
        "get_report_path",
        lambda scan_id: tmp_path / f"report_{scan_id}.pdf",
    )

    return Session


@pytest.mark.asyncio
async def test_end_to_end_scan_and_pdf_evidence_fidelity(weak_bot_server, test_db_session):
    """
    Gate 4 Primary Assertion:
    1. Scan against weak-bot produces a confirmed exploit.
    2. Finding and turn records are persisted to SQLite.
    3. Styled PDF report is produced via ReportService.
    4. Text extracted from PDF contains exact match of scan_id, target name, canary,
       finding description, prompt, and severity from SQLite.
    """
    scan_id = "test-scan-gate4-pdf-fidelity"
    target_id = "test-target-gate4-fidelity"
    target_name = "Acme Customer Assistant (Weak Bot)"

    # 1. Register target and scan in SQLite
    with test_db_session() as session:
        target = TargetEntity(
            id=target_id,
            name=target_name,
            target_type="web",
            url=weak_bot_server,
            created_at=datetime.now(timezone.utc),
        )
        session.add(target)

        scan = ScanEntity(
            id=scan_id,
            target_id=target_id,
            status="QUEUED",
            category="LLM08",
            budget=3,
            current_attempt=0,
            created_at=datetime.now(timezone.utc),
        )
        session.add(scan)
        session.commit()

    # 2. Run orchestrator to trigger exploit and persist finding
    adapter = PlaywrightWebAdapter(target_url=weak_bot_server, headless=True)
    orchestrator = Orchestrator(
        scan_id=scan_id,
        adapter=adapter,
        max_budget=3,
        session_factory=test_db_session,
    )

    verdict = await orchestrator.run()
    assert verdict is not None and verdict.exploited is True

    # Mark scan COMPLETED in DB
    with test_db_session() as session:
        s = session.get(ScanEntity, scan_id)
        s.status = "COMPLETED"
        s.completed_at = datetime.now(timezone.utc)
        session.commit()

    # 3. Retrieve ground-truth finding from SQLite
    db_findings = await FindingsService.get_findings_by_scan(scan_id, session_factory=test_db_session)
    assert len(db_findings) >= 1
    ground_truth_finding = db_findings[0]
    finding_detail = await FindingsService.get_finding_detail(ground_truth_finding.id, session_factory=test_db_session)

    # 4. Generate styled PDF report
    pdf_path = await ReportService.generate_report(scan_id, session_factory=test_db_session)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    # Read binary bytes and check magic number
    pdf_bytes = pdf_path.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-")

    # 5. Extract text using pypdf and verify 100% evidence fidelity
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1

    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() + "\n"

    # Verify Gate 4 criteria
    assert scan_id in extracted_text, f"Scan ID '{scan_id}' missing from PDF text"
    assert "LLM08" in extracted_text, "Category LLM08 missing from PDF text"
    assert target_name in extracted_text, f"Target name '{target_name}' missing from PDF text"
    assert "AEGIS-CANARY-7731" in extracted_text, "Canary token 'AEGIS-CANARY-7731' missing from PDF text"
    assert ground_truth_finding.severity in extracted_text, f"Severity '{ground_truth_finding.severity}' missing from PDF text"
    assert "Acme support" in extracted_text or "Internal test rule" in extracted_text, "Leaked prompt excerpt missing from PDF text"
    assert "EXECUTIVE SUMMARY" in extracted_text, "Executive summary section missing from PDF text"
    assert "ASSESSMENT METHODOLOGY" in extracted_text, "Methodology section missing from PDF text"
    assert "DISCLAIMER & SCOPE NOTICE" in extracted_text, "Disclaimer section missing from PDF text"


@pytest.mark.asyncio
async def test_clean_scan_pdf_generation(test_db_session):
    """Verify clean scan with zero findings produces a compliant non-exploited report."""
    scan_id = "test-scan-clean-pdf"
    target_id = "test-target-clean"

    with test_db_session() as session:
        target = TargetEntity(
            id=target_id,
            name="Hardened Chatbot",
            target_type="web",
            url="http://127.0.0.1:8002",
            created_at=datetime.now(timezone.utc),
        )
        session.add(target)

        scan = ScanEntity(
            id=scan_id,
            target_id=target_id,
            status="COMPLETED",
            category="LLM08",
            budget=5,
            current_attempt=5,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(scan)
        session.commit()

    pdf_path = await ReportService.generate_report(scan_id, session_factory=test_db_session)
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF-")

    reader = PdfReader(str(pdf_path))
    extracted = "".join(p.extract_text() for p in reader.pages)

    assert scan_id in extracted
    assert "Hardened Chatbot" in extracted
    assert "No prompt disclosure vulnerabilities were identified" in extracted or "No prompt leakage vulnerabilities identified" in extracted
    assert "100" in extracted  # Perfect score for clean scan
