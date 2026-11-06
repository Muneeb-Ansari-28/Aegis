"""Unit tests for YAML Signature Matching."""
import pytest
from app.recon.fingerprint import SignatureMatcher


def test_signature_matcher_loads_default_yaml():
    matcher = SignatureMatcher()
    assert len(matcher.signatures) >= 8
    sig_ids = [s["id"] for s in matcher.signatures]
    assert "sig_openai_compat" in sig_ids
    assert "sig_streamlit" in sig_ids
    assert "sig_gradio" in sig_ids
    assert "sig_fastapi_backend" in sig_ids


def test_match_openai_compatible_endpoint():
    matcher = SignatureMatcher()
    observed = {
        "paths": ["/v1/chat/completions", "/docs"],
        "headers": {"openai-version": "2024-02-01"},
    }
    matches = matcher.match(observed)
    match_ids = [m.signature_id for m in matches]
    assert "sig_openai_compat" in match_ids
    matched_sig = next(m for m in matches if m.signature_id == "sig_openai_compat")
    assert matched_sig.confidence >= 0.90
    assert matched_sig.implies.get("endpoint") == "openai_compat"


def test_match_streamlit_framework():
    matcher = SignatureMatcher()
    observed = {
        "websocket_paths": ["/_stcore/stream"],
        "dom": ["div.stApp"],
        "globals": ["Streamlit"],
    }
    matches = matcher.match(observed)
    match_ids = [m.signature_id for m in matches]
    assert "sig_streamlit" in match_ids
    matched = next(m for m in matches if m.signature_id == "sig_streamlit")
    assert matched.implies.get("framework") == "streamlit"
    assert matched.implies.get("streaming") == "websocket"


def test_match_rag_payload_keys():
    matcher = SignatureMatcher()
    observed = {
        "response_keys": ["citations", "sources", "text"],
    }
    matches = matcher.match(observed)
    match_ids = [m.signature_id for m in matches]
    assert "sig_rag_response_keys" in match_ids
    matched = next(m for m in matches if m.signature_id == "sig_rag_response_keys")
    assert matched.implies.get("rag") is True


def test_match_session_memory():
    matcher = SignatureMatcher()
    observed = {
        "payload_keys": ["session_id", "messages"],
    }
    matches = matcher.match(observed)
    match_ids = [m.signature_id for m in matches]
    assert "sig_session_memory" in match_ids
    matched = next(m for m in matches if m.signature_id == "sig_session_memory")
    assert matched.implies.get("memory") is True

