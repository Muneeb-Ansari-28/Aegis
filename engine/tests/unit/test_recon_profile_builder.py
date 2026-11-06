"""Unit tests for Deterministic Profile Builder and Confidence Corroboration."""
import pytest
from app.recon.fingerprint import SignatureMatch
from app.recon.profile_builder import ProfileBuilder, combine_confidences
from app.recon.probe_runner import ProbeAnalysis, ProbeRunResult
from app.recon.static_scanner import StaticScanResult


def test_combine_confidences():
    # 0.8 and 0.8 should boost towards 0.96
    combined = combine_confidences(0.8, 0.8)
    assert combined == pytest.approx(0.96, rel=1e-2)
    # Never exceeds 0.99
    assert combine_confidences(0.99, 0.99) == 0.99


def test_profile_builder_corroborates_rag_signals():
    # Static scan detected ChromaDB (conf 0.95)
    static_res = StaticScanResult(
        project_path="/mock",
        has_rag=True,
        has_vector_db=True,
        vector_db_names=["ChromaDB"],
        evidence=["requirements.txt has chromadb"],
    )

    # Active probe also observed citations (conf 0.75)
    probe_analysis = ProbeAnalysis(
        rag_detected=True,
        rag_confidence=0.75,
        evidence=["Found citation links"],
    )
    probe_result = ProbeRunResult(analysis=probe_analysis)

    builder = ProfileBuilder(
        target_id="tgt-1",
        target_url="http://localhost:8000",
        static_result=static_res,
        probe_result=probe_result,
    )
    profile = builder.build()

    assert profile.has_rag.detected is True
    # Confidence should be boosted due to multiple corroborating tiers
    assert profile.has_rag.confidence >= 0.95
    assert profile.has_rag.source == "corroborated"
    assert profile.has_vector_db.detected is True
    assert profile.has_vector_db.value == "ChromaDB"


def test_profile_builder_unknown_safe_fallback():
    # No signals detected, no static scan
    builder = ProfileBuilder(
        target_id="tgt-2",
        target_url="http://example.com",
    )
    profile = builder.build()

    # RAG not detected, but confidence is low (unknown != absent)
    assert profile.has_rag.detected is False
    assert profile.has_rag.confidence < 0.60
    assert "unknown" in profile.has_rag.evidence[0].lower()

