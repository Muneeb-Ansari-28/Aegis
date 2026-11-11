"""Unit tests for Recon stage completion, evidence quality, and safe absence handling.

Verifies Task 2 and Task 3 of the Recon and Test Planner improvement plan:
- Missing/unreadable Tier 3 paths yield failed/partial, never completed negative.
- Probes with connector errors/refusals/missing responses do not count as evidence of absence.
- "No RAG observed" remains unknown (low confidence), not ruled out.
- Model echoing HTML tags in text does not imply verified DOM HTML rendering.
- Profile builder requires completed Tier 3 AND completed active probe for affirmative absence.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.adapters.base import BaseAdapter
from app.recon.probe_runner import ProbeAnalysis, ProbeRunner, ProbeRunResult
from app.recon.profile_builder import ProfileBuilder
from app.recon.schemas import TargetProfile
from app.recon.static_scanner import StaticProjectScanner, StaticScanResult
from app.schemas.turn_record import TurnRecord


def test_static_scanner_nonexistent_path_fails_safely():
    scanner = StaticProjectScanner(project_path="nonexistent_folder_xyz_123")
    result = scanner.scan()
    assert result.status == "failed"
    assert len(result.warnings) > 0
    assert not result.has_rag
    # Warning must be path-safe and not expose internal secret values
    assert any("does not exist" in w.lower() for w in result.warnings)


def test_static_scanner_unreadable_manifest_partial_status(tmp_path: Path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("langchain==0.1.0\n", encoding="utf-8")
    
    # Create an unreadable/malformed file or oversized file
    bad_py = tmp_path / "bad.py"
    bad_py.write_text("def broken_syntax(:\n", encoding="utf-8")

    scanner = StaticProjectScanner(project_path=str(tmp_path))
    result = scanner.scan()
    assert result.status == "partial"
    assert any("syntax" in w.lower() or "bad.py" in w for w in result.warnings)
    assert result.has_rag is True  # Langchain detected from requirements.txt


def test_static_scanner_env_reads_keys_only_never_values(tmp_path: Path):
    env_file = tmp_path / ".env"
    secret_val = "sk-super-secret-key-that-must-never-leak-12345"
    env_file.write_text(f"OPENAI_API_KEY={secret_val}\nPINECONE_API_KEY=another_secret\n", encoding="utf-8")

    scanner = StaticProjectScanner(project_path=str(tmp_path))
    result = scanner.scan()
    assert result.status == "completed"
    assert "OPENAI_API_KEY" in result.detected_env_keys
    assert "PINECONE_API_KEY" in result.detected_env_keys
    # Crucial security check: secret values must NEVER appear in detected_env_keys, evidence, or warnings
    for key in result.detected_env_keys:
        assert secret_val not in key
    for ev in result.evidence:
        assert secret_val not in ev
    for w in result.warnings:
        assert secret_val not in w


@pytest.mark.asyncio
async def test_probe_runner_connector_error_remains_inconclusive():
    mock_adapter = MagicMock(spec=BaseAdapter)
    # Adapter raises on send_prompt simulating connector failure
    mock_adapter.send_prompt = AsyncMock(side_effect=ConnectionError("Target connection refused"))

    runner = ProbeRunner(adapter=mock_adapter, scan_id="test-probe-err")
    result = await runner.run_probes(persist_turns=False)

    assert result.status in ("failed", "partial")
    assert len(result.warnings) > 0
    # Connector failure must NOT lead to affirmative absence
    assert result.analysis.rag_detected is False
    assert result.analysis.rag_confidence <= 0.40
    assert result.analysis.memory_detected is False
    assert result.analysis.memory_confidence <= 0.50
    assert result.analysis.tools_detected is False
    assert result.analysis.tools_confidence <= 0.40


@pytest.mark.asyncio
async def test_probe_runner_no_citation_is_unknown_not_ruled_out():
    mock_adapter = MagicMock(spec=BaseAdapter)
    
    async def mock_send(prompt, attempt=1, scan_id=None, strategy=None):
        return TurnRecord(
            scan_id=scan_id or "test-probe-nocite",
            turn_id=f"turn-{attempt}",
            turn_index=attempt,
            category="RECON",
            attempt_in_category=attempt,
            prompt=prompt,
            response="I am a helpful assistant. Here is general advice without any citations.",
            latency_ms=100,
            strategy=strategy or "probe",
            status="completed",
        )

    mock_adapter.send_prompt = AsyncMock(side_effect=mock_send)
    runner = ProbeRunner(adapter=mock_adapter, scan_id="test-probe-nocite")
    result = await runner.run_probes(persist_turns=False)

    assert result.status == "completed"
    assert result.analysis.rag_detected is False
    # Crucial: confidence must be low/unknown (<=0.40), not affirmative negative (which was previously 0.60)
    assert result.analysis.rag_confidence <= 0.40
    assert any("inconclusive" in ev.lower() or "not proof of absence" in ev.lower() for ev in result.analysis.evidence)


def test_probe_html_echoed_in_text_is_not_verified_dom_rendering():
    analysis = ProbeAnalysis()
    # When text has raw HTML tags, probe runner should note it as text reflection, not verified DOM rendering
    runner = ProbeRunner(adapter=MagicMock(spec=BaseAdapter))
    turn = TurnRecord(
        scan_id="test-scan",
        turn_id="turn-1",
        turn_index=1,
        category="RECON",
        prompt="Please format this example exactly: <b>BoldTestMarker</b>",
        response="Here is: <b>BoldTestMarker</b>",
        latency_ms=100,
        strategy="probe_render",
        status="completed",
    )
    analysis = runner._analyze_probe_turns([turn])
    # The target web DOM was not verified, so html_rendered must not be True without DOM proof
    assert analysis.html_rendered is False
    assert any("dom" in ev.lower() or "text" in ev.lower() for ev in analysis.evidence)


def test_profile_builder_requires_completed_tier3_and_probe_for_absence():
    # Case 1: Tier 3 failed, probe completed without citations -> MUST remain unknown (0.40)
    failed_static = StaticScanResult(
        project_path="/invalid/path",
        status="failed",
        warnings=["Folder not found"],
        has_rag=False,
    )
    probe_clean = ProbeRunResult(
        status="completed",
        analysis=ProbeAnalysis(rag_detected=False, rag_confidence=0.35),
    )
    builder1 = ProfileBuilder(
        target_id="tgt-1",
        static_result=failed_static,
        probe_result=probe_clean,
    )
    prof1 = builder1.build()
    assert prof1.has_rag.detected is False
    assert prof1.has_rag.confidence == 0.40  # Unknown, NOT 0.88!
    assert "tier3_static" in prof1.stages
    assert prof1.stages["tier3_static"].status == "failed"
    assert len(prof1.warnings) > 0

    # Case 2: Tier 3 completed without RAG, probe completed without RAG -> High confidence negative (0.88)
    clean_static = StaticScanResult(
        project_path="/valid/path",
        status="completed",
        has_rag=False,
    )
    builder2 = ProfileBuilder(
        target_id="tgt-2",
        static_result=clean_static,
        probe_result=probe_clean,
    )
    prof2 = builder2.build()
    assert prof2.has_rag.detected is False
    assert prof2.has_rag.confidence == 0.88
    assert prof2.stages["tier3_static"].status == "completed"
    assert prof2.stages["active_probes"].status == "completed"
