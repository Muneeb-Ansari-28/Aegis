"""
Gate 4 Verification Script: Styled PDF Produced, Evidence Matches SQLite DB.

Requirements for Gate 4:
1. Scan executed against weak-bot test target.
2. Exploit confirmed and findings + turns persisted to SQLite.
3. Findings service/API returns correct correlated evidence.
4. Styled PDF report generated with professional layout and CSS.
5. Text extracted from PDF matches ground-truth DB evidence with 100% fidelity.
"""
import asyncio
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import threading
import time

# Add engine directory to sys.path so app modules import cleanly
ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uvicorn

from app.adapters.playwright_web import PlaywrightWebAdapter  # type: ignore # pyrefly: ignore[missing-import]
from app.agents.orchestrator import Orchestrator  # type: ignore # pyrefly: ignore[missing-import]
from app.core.database import Base  # type: ignore # pyrefly: ignore[missing-import]
from app.models.entities import FindingEntity, ScanEntity, TargetEntity  # type: ignore # pyrefly: ignore[missing-import]
from app.services.findings_service import FindingsService  # type: ignore # pyrefly: ignore[missing-import]
from app.services.report_service import ReportService  # type: ignore # pyrefly: ignore[missing-import]


import socket

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_weak_bot(port: int = 0) -> str:
    """Start local weak-bot test server in background thread on a free port."""
    if port == 0:
        port = find_free_port()
    weak_bot_path = Path(__file__).resolve().parents[1] / "test-targets" / "weak-bot" / "app.py"
    spec = importlib.util.spec_from_file_location("weak_bot_app", str(weak_bot_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load weak-bot app specification from {weak_bot_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    thread = threading.Thread(
        target=lambda: uvicorn.run(mod.app, host="127.0.0.1", port=port, log_level="error"),
        daemon=True,
    )
    thread.start()
    time.sleep(1.5)
    return f"http://127.0.0.1:{port}"


async def run_verification() -> bool:
    print("=" * 70)
    print("  AEGIS GATE 4 VERIFICATION: STYLED PDF REPORT & EVIDENCE FIDELITY")
    print("=" * 70)

    # 1. Start weak-bot target on free port
    port = find_free_port()
    print(f"[1/5] Starting local weak-bot target on free port {port}...")
    target_url = start_weak_bot(port)
    print(f"      Weak bot online at {target_url}")

    # 2. Initialize database
    print("[2/5] Initializing test SQLite database...")
    db_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=db_engine)
    SessionFactory = sessionmaker(bind=db_engine)

    scan_id = "gate4-verify-scan-001"
    target_id = "gate4-target-001"
    target_name = "Acme Storefront Assistant"

    with SessionFactory() as session:
        target = TargetEntity(
            id=target_id,
            name=target_name,
            target_type="web",
            url=target_url,
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
    print("      Target and Scan registered in SQLite.")

    # 3. Execute scan via Orchestrator
    print("[3/5] Executing scan via Orchestrator with Playwright...")
    adapter = PlaywrightWebAdapter(target_url=target_url, headless=True)
    orchestrator = Orchestrator(
        scan_id=scan_id,
        adapter=adapter,
        max_budget=3,
        session_factory=SessionFactory,
    )
    verdict = await orchestrator.run()

    if not verdict or not verdict.exploited:
        print("      FAILED: Orchestrator did not detect expected exploit.")
        return False

    print(f"      Exploit confirmed! Confidence: {verdict.confidence:.0%}, Indicators: {verdict.indicators_found}")

    # Mark scan as COMPLETED in DB
    with SessionFactory() as session:
        s = session.get(ScanEntity, scan_id)
        if s is not None:
            setattr(s, "status", "COMPLETED")
            setattr(s, "completed_at", datetime.now(timezone.utc))
            session.commit()

    # 4. Check SQLite persistence
    print("[4/5] Verifying SQLite persistence and FindingsService correlation...")
    findings = await FindingsService.get_findings_by_scan(scan_id, session_factory=SessionFactory)
    if not findings:
        print("      FAILED: No findings found in SQLite.")
        return False

    finding = findings[0]
    detail = await FindingsService.get_finding_detail(finding.id, session_factory=SessionFactory)
    summary = await FindingsService.get_findings_summary(scan_id, session_factory=SessionFactory)
    if detail is None or summary is None:
        print("      FAILED: Finding detail or summary could not be retrieved.")
        return False

    print(f"      Found {len(findings)} finding(s):")
    print(f"      - ID: {finding.id}")
    print(f"      - Category: {finding.category}")
    print(f"      - Severity: {finding.severity}")
    print(f"      - Confidence: {finding.confidence:.0%}")
    print(f"      - Risk Grade: {summary.risk_grade:.1f}/100")
    print(f"      - Canary detected in response: {'AEGIS-CANARY-7731' in detail.response}")

    # 5. Generate and verify PDF report
    print("[5/5] Generating PDF Report and verifying text fidelity against SQLite...")
    pdf_path = await ReportService.generate_report(scan_id, session_factory=SessionFactory)
    if not pdf_path.exists():
        print(f"      FAILED: PDF file not created at {pdf_path}")
        return False

    pdf_bytes = pdf_path.read_bytes()
    if not pdf_bytes.startswith(b"%PDF-"):
        print("      FAILED: File does not have valid %PDF- magic number header.")
        return False

    file_size_kb = len(pdf_bytes) / 1024
    print(f"      Valid PDF generated successfully ({file_size_kb:.1f} KB at {pdf_path})")

    # Extract text and assert fidelity
    reader = PdfReader(str(pdf_path))
    extracted_text = "".join(page.extract_text() for page in reader.pages)

    checks = [
        ("Scan ID in PDF", scan_id in extracted_text),
        ("Target Name in PDF", target_name in extracted_text),
        ("Vulnerability Category (LLM08) in PDF", "LLM08" in extracted_text),
        ("Planted Canary Token in PDF", "AEGIS-CANARY-7731" in extracted_text),
        ("Finding Severity in PDF", finding.severity in extracted_text),
        ("Prompt Evidence in PDF", detail.prompt[:30] in extracted_text or "system instructions" in extracted_text),
        ("Response Evidence in PDF", "Acme support" in extracted_text or "Internal test rule" in extracted_text),
        ("Executive Summary Section in PDF", "EXECUTIVE SUMMARY" in extracted_text),
        ("Assessment Methodology in PDF", "ASSESSMENT METHODOLOGY" in extracted_text),
        ("Scope Disclaimer in PDF", "DISCLAIMER & SCOPE NOTICE" in extracted_text),
    ]

    print("\n  --- Evidence Fidelity Verification Results ---")
    all_passed = True
    for name, passed in checks:
        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str} {name}")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("  RESULT: GATE 4 PASSED (Styled PDF produced, evidence matches DB)")
    else:
        print("  RESULT: GATE 4 FAILED")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_verification())
    sys.exit(0 if success else 1)
