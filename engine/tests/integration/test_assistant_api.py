"""Integration tests for Aegis Assistant API and RAG pipeline."""
import pytest
from fastapi.testclient import TestClient

from app.api.v1.router import app
from app.agents.assistant_agent import NO_DOCS_REPLY
from app.rag.vector_store import VectorStore


@pytest.fixture(scope="module")
def client():
    """FastAPI test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_assistant_status_endpoint(client: TestClient):
    """Verify /api/v1/assistant/status returns ready status, chunk count, and model names."""
    resp = client.get("/api/v1/assistant/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] in ("ready", "degraded")
    assert data["kb_chunks_indexed"] >= 100
    assert "nomic-embed-text" in data["embed_model"]
    assert "llama3.2" in data["assistant_model"]


def test_assistant_chat_empty_message_returns_400(client: TestClient):
    """Verify empty query returns 400 Bad Request."""
    resp = client.post("/api/v1/assistant/chat", json={"message": "   "})
    assert resp.status_code == 400


def test_assistant_chat_all_ten_owasp_categories(client: TestClient):
    """Verify all 10 OWASP 2026 categories can be queried and return grounded answers with citations."""
    categories = [
        ("LLM01:2026", "Prompt Injection"),
        ("LLM02:2026", "Sensitive Information Disclosure"),
        ("LLM03:2026", "Excessive Agency"),
        ("LLM04:2026", "Supply Chain"),
        ("LLM05:2026", "Data and Model Poisoning"),
        ("LLM06:2026", "Unbounded Consumption"),
        ("LLM07:2026", "Misinformation"),
        ("LLM08:2026", "Hidden Context Exposure"),
        ("LLM09:2026", "Vector and Embedding Weaknesses"),
        ("LLM10:2026", "Improper Output Handling"),
    ]

    for cat_id, cat_name in categories:
        resp = client.post(
            "/api/v1/assistant/chat",
            json={"message": f"What is {cat_id} {cat_name}?"},
        )
        assert resp.status_code == 200, f"Query failed for {cat_id}"
        data = resp.json()
        assert len(data["reply"]) > 20, f"Empty reply for {cat_id}"
        assert len(data["source_ids"]) > 0, f"No source chunks retrieved for {cat_id}"

        # Verify citation references the risk
        citations = data["citations"]
        assert len(citations) > 0, f"No structured citations for {cat_id}"
        has_risk_cite = any(c.get("risk_id") == cat_id for c in citations)
        assert has_risk_cite, f"Expected citation with risk_id {cat_id}"


def test_assistant_chat_legacy_system_prompt_leakage_crosswalk(client: TestClient):
    """Verify query for legacy LLM07:2025 System Prompt Leakage maps to LLM08:2026."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is LLM07 System Prompt Leakage in the 2025 list?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"].lower()

    # Must explain that it maps to LLM08 / Hidden Context Exposure
    assert "llm08" in reply or "hidden context" in reply
    assert len(data["source_ids"]) > 0


def test_assistant_chat_scan_capability_honesty(client: TestClient):
    """Verify assistant honestly states only LLM08 is scanned and other categories are in development."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Can Aegis scan for LLM01 Prompt Injection?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"].lower()

    # Must acknowledge knowledge of LLM01 but state scanning is in development or not yet implemented
    assert "llm08" in reply or "development" in reply or "hidden context" in reply or "not" in reply


def test_assistant_chat_operational_calibration_question(client: TestClient):
    """Verify assistant answers Playwright browser calibration questions from Aegis docs."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "How do I calibrate a web target in Aegis?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"].lower()

    # Must cite Playwright calibration / input / click
    assert "calibration" in reply or "playwright" in reply or "click" in reply
    assert any(c.get("source") == "aegis" for c in data["citations"])


def test_assistant_chat_out_of_scope_fallback(client: TestClient):
    """Verify off-topic questions trigger the no-documentation fallback."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is the capital of France?"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Expect no documentation fallback
    assert data["reply"] == NO_DOCS_REPLY
    assert data["source_ids"] == []


def test_assistant_chat_simplify_mode(client: TestClient):
    """Verify explicit simplify mode rewrites previous answer with same citations."""
    store = VectorStore()
    llm08_chunks = store.collection.get(where={"risk_id": "LLM08:2026"})["ids"][:2]

    history = [
        {"role": "user", "text": "What is LLM08:2026?"},
        {
            "role": "assistant",
            "text": "Hidden Context Exposure (LLM08:2026) is unauthorized extraction of non-user-facing context.",
            "source_ids": llm08_chunks,
        },
    ]

    resp = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Explain this more simply",
            "history": history,
            "mode": "simplify",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "simplify"
    assert len(data["reply"]) > 20
    assert len(data["source_ids"]) >= 2
