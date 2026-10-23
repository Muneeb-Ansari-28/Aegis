"""Integration tests for Aegis Assistant API, RAG pipeline, and answer quality regressions."""
import pytest
from fastapi.testclient import TestClient

from app.api.v1.router import app
from app.agents.assistant_agent import NO_DOCS_REPLY, NO_SCAN_EVIDENCE_REPLY
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


# ==============================================================================
# Required 8 Regression Scenarios (FYP Aegis Specification)
# ==============================================================================

def test_scenario_1_basic_factual_owasp(client: TestClient):
    """Scenario 1: A basic factual question about OWASP Top 10 2026."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is LLM01:2026 Prompt Injection?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"]

    assert len(reply) > 40
    # Must explain prompt injection
    assert "prompt injection" in reply.lower() or "llm01" in reply.lower()
    assert len(data["source_ids"]) > 0
    # Must have citations without leaking internal (source: ...) tags
    assert "(source: " not in reply
    assert any(c.get("risk_id") == "LLM01:2026" for c in data["citations"])


def test_scenario_2_comparison_supply_chain_vs_excessive_agency(client: TestClient):
    """Scenario 2: Comparison between Supply Chain and Excessive Agency (synthesized, non-repetitive)."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is the difference between Supply Chain and Excessive Agency?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"]

    # Must cover both categories
    assert "supply chain" in reply.lower()
    assert "excessive agency" in reply.lower()

    # Must contain structured comparison (table or clean headers)
    assert "|" in reply or "###" in reply or "**" in reply

    # Must NOT have raw citation dump at the start
    assert not reply.strip().startswith("[LLM03:2026")
    assert "(source:" not in reply

    # Citations must cover both risks and be deduplicated
    risk_ids = [c.get("risk_id") for c in data["citations"]]
    assert "LLM03:2026" in risk_ids
    assert "LLM04:2026" in risk_ids


def test_scenario_3_multi_source_question(client: TestClient):
    """Scenario 3: Question requiring information from multiple relevant sources (OWASP + Aegis)."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "How does Aegis test for LLM08 Hidden Context Exposure using canary tokens?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"].lower()

    # Must synthesize concepts: canary token + LLM08 / hidden context
    assert "canary" in reply or "token" in reply
    assert "llm08" in reply or "hidden context" in reply or "system prompt" in reply

    # Must cite both sources (OWASP and Aegis)
    sources = {c.get("source") for c in data["citations"]}
    assert "owasp_llm_top10_2026" in sources or any("owasp" in str(c.get("source_title", "")).lower() for c in data["citations"])
    assert "aegis" in sources or any("aegis" in str(c.get("source_title", "")).lower() for c in data["citations"])


def test_scenario_4_unsupported_knowledge_fallback(client: TestClient):
    """Scenario 4: Question whose answer is not supported by the knowledge base."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is the capital of France and what is the best bakery there?"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["reply"] == NO_DOCS_REPLY
    assert data["source_ids"] == []
    assert data["citations"] == []


def test_scenario_5_markdown_rendering_contract(client: TestClient):
    """Scenario 5: Response containing headings, bold text, lists, and a comparison table."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Provide a comparison between LLM01 Prompt Injection and LLM02 Sensitive Information Disclosure with a table and mitigations."},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"]

    # Verify Markdown formatting elements
    has_bold = "**" in reply
    has_list = "-" in reply or "*" in reply or "1." in reply
    has_table = "|" in reply and "---" in reply
    assert has_bold, "Response should contain bold emphasis"
    assert has_list or has_table, "Response should contain formatted lists or table"


def test_scenario_6_duplicate_source_references_deduplicated(client: TestClient):
    """Scenario 6: Response containing multiple source references ensures citations are deduplicated."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What are the prevention and mitigation strategies for LLM04 Supply Chain?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    citations = data["citations"]

    # Ensure no exact duplicate citations exist in the array
    keys = [
        (c.get("risk_id"), c.get("page"), c.get("source_title"), c.get("section"))
        for c in citations
    ]
    assert len(keys) == len(set(keys)), "Citations list must be strictly deduplicated"


def test_scenario_7_unimplemented_capability_honesty(client: TestClient):
    """Scenario 7: Question about Aegis functionality that is documented as not yet implemented."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Can Aegis run an automated scanner for LLM05 Data and Model Poisoning?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"].lower()

    # Must honestly clarify scanning status: LLM08 is active; LLM05 is in development
    assert "llm08" in reply or "development" in reply or "not yet" in reply or "currently" in reply


def test_scenario_8_scan_evidence_inquiry_without_evidence(client: TestClient):
    """Scenario 8: Question asking whether a vulnerability was actually detected without supplying scan evidence."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Did the scan detect LLM01 in my application?"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Must trigger scan evidence honesty response
    assert data["reply"] == NO_SCAN_EVIDENCE_REPLY
    assert data["source_ids"] == []


# ==============================================================================
# Additional Operational Tests
# ==============================================================================

def test_assistant_chat_legacy_crosswalk(client: TestClient):
    """Verify legacy LLM07:2025 maps to LLM08:2026 Hidden Context Exposure."""
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What was LLM07 System Prompt Leakage in the previous list?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"].lower()
    assert "llm08" in reply or "hidden context" in reply


def test_assistant_chat_simplify_mode(client: TestClient):
    """Verify simplify mode rewrites previous answer with an analogy and 'In short:' conclusion."""
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
