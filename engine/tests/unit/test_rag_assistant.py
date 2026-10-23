"""Unit tests for Aegis RAG Assistant subsystem."""
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union
import pytest

from app.agents.assistant_agent import (
    AssistantAgent,
    NO_DOCS_REPLY,
    NO_SCAN_EVIDENCE_REPLY,
    OWASP_NAME_MAP,
    LEGACY_RENAME_MAP,
    SIMPLIFY_RE,
    SCAN_EVIDENCE_INQUIRY_RE,
    clean_response,
    deduplicate_citations,
)
from app.rag.indexer import (
    generate_chunk_id,
    split_into_chunks,
    parse_owasp_markdown,
    parse_aegis_markdown,
)
from app.rag.retriever import AssistantRetriever
from app.rag.vector_store import VectorStore
from app.schemas.assistant import (
    ChatMessage,
    CitationItem,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantStatusResponse,
)


def test_deterministic_chunk_id_generation():
    """Verify chunk ID generation is deterministic and idempotent."""
    id1 = generate_chunk_id("owasp", "LLM08:2026", "Mitigations", 0, "Test chunk content text")
    id2 = generate_chunk_id("owasp", "LLM08:2026", "Mitigations", 0, "Test chunk content text")
    id3 = generate_chunk_id("owasp", "LLM08:2026", "Mitigations", 1, "Test chunk content text")
    id4 = generate_chunk_id("owasp", "LLM01:2026", "Mitigations", 0, "Test chunk content text")

    assert id1 == id2, "Identical inputs must yield identical IDs"
    assert id1 != id3, "Different chunk index must yield different IDs"
    assert id1 != id4, "Different risk ID must yield different IDs"
    assert "LLM08_2026" in id1


def test_split_into_chunks_word_boundaries():
    """Verify that split_into_chunks honors word thresholds and maintains coherence."""
    words = [f"word{i}" for i in range(100)]
    short_text = " ".join(words)
    chunks = split_into_chunks(short_text, max_words=150)
    assert len(chunks) == 1
    assert chunks[0] == short_text

    long_words = [f"word{i}" for i in range(500)]
    long_text = " ".join(long_words)
    chunks = split_into_chunks(long_text, max_words=200, overlap=20)
    assert len(chunks) >= 3
    # Verify no empty chunks
    for c in chunks:
        assert len(c.split()) <= 200
        assert len(c.split()) > 0


def test_parse_owasp_markdown_extracts_all_ten_risks():
    """Verify that parse_owasp_markdown finds all ten 2026 OWASP risk categories."""
    owasp_file = Path(__file__).resolve().parent.parent.parent / "knowledge" / "owasp" / "OWASP-LLM-Top-10-2026.md"
    assert owasp_file.exists(), f"OWASP file missing at {owasp_file}"

    chunks = parse_owasp_markdown(owasp_file)
    assert len(chunks) > 50, f"Expected >50 chunks, got {len(chunks)}"

    found_risks = {c[2].get("risk_id") for c in chunks if c[2].get("risk_id")}
    for i in range(1, 11):
        expected_id = f"LLM{i:02d}:2026"
        assert expected_id in found_risks, f"Missing risk {expected_id} from OWASP parsed chunks"

    # Verify pages are preserved
    pages = [c[2].get("page") for c in chunks if c[2].get("page")]
    assert len(pages) > 0
    assert any(p == 47 for p in pages), "Page 47 (LLM08 start) should be present"


def test_parse_owasp_markdown_extracts_simple_companion_chunks():
    """Verify that companion plain-language chunks are tagged with level=simple."""
    owasp_file = Path(__file__).resolve().parent.parent.parent / "knowledge" / "owasp" / "OWASP-LLM-Top-10-2026.md"
    chunks = parse_owasp_markdown(owasp_file)

    simple_chunks = [c for c in chunks if c[2].get("level") == "simple"]
    assert len(simple_chunks) >= 10, f"Expected at least 10 simple companion chunks, got {len(simple_chunks)}"

    simple_risks = {c[2].get("risk_id") for c in simple_chunks if c[2].get("risk_id")}
    for i in range(1, 11):
        expected_id = f"LLM{i:02d}:2026"
        assert expected_id in simple_risks, f"Missing simple companion chunk for {expected_id}"


def test_parse_aegis_markdown_extracts_clean_sections():
    """Verify that Aegis documentation files parse into source=aegis chunks."""
    aegis_file = Path(__file__).resolve().parent.parent.parent / "knowledge" / "aegis" / "aegis_overview.md"
    assert aegis_file.exists()

    chunks = parse_aegis_markdown(aegis_file)
    assert len(chunks) >= 3
    for c_id, text, meta in chunks:
        assert meta["source"] == "aegis"
        assert "Aegis Documentation" in text
        assert meta["level"] == "standard"


def test_detect_intent_phrasing():
    """Verify intent detection identifies standard ask vs simplify requests."""
    agent = AssistantAgent()

    assert agent.detect_intent("What is LLM01:2026?") == "ask"
    assert agent.detect_intent("How do I calibrate a target?") == "ask"
    assert agent.detect_intent("What are its mitigations?") == "ask"

    # Simplify requests
    assert agent.detect_intent("Explain this more simply") == "simplify"
    assert agent.detect_intent("I don't understand") == "simplify"
    assert agent.detect_intent("Can you make it simpler?") == "simplify"
    assert agent.detect_intent("Explain vector embeddings like I'm five") == "simplify"
    assert agent.detect_intent("Break it down for a beginner") == "simplify"
    assert agent.detect_intent("In plain English please") == "simplify"
    assert agent.detect_intent("Any message", mode="simplify") == "simplify"


def test_detect_double_simplify():
    """Verify double-simplify detection triggers when previous user turn was also simplify."""
    agent = AssistantAgent()

    # User message contains "even simpler"
    assert agent.detect_double_simplify("Make it even simpler please", []) is True

    # Preceding user turn was simplify
    history: List[Union[ChatMessage, Dict[str, Any]]] = [
        ChatMessage(role="user", text="Explain it simply"),
        ChatMessage(role="assistant", text="Here is a simple explanation..."),
    ]
    assert agent.detect_double_simplify("Still don't get it", history) is True

    # Preceding user turn was standard ask
    history_standard: List[Union[ChatMessage, Dict[str, Any]]] = [
        ChatMessage(role="user", text="What is LLM08:2026?"),
        ChatMessage(role="assistant", text="LLM08 is Hidden Context Exposure..."),
    ]
    assert agent.detect_double_simplify("What about LLM01?", history_standard) is False


def test_normalize_query_legacy_mappings():
    """Verify query normalization maps legacy 2025 terms to 2026 canonical identifiers."""
    agent = AssistantAgent()

    q1 = agent.normalize_query("What is LLM07 system prompt leakage?")
    assert "LLM08:2026 Hidden Context Exposure" in q1

    q2 = agent.normalize_query("Explain LLM06 excessive agency")
    assert "LLM03:2026 Excessive Agency" in q2

    q3 = agent.normalize_query("What is LLM05 improper output handling?")
    assert "LLM10:2026 Improper Output Handling" in q3

    # Bare ID expansion
    q4 = agent.normalize_query("Tell me about LLM02")
    assert "LLM02:2026 Sensitive Information Disclosure" in q4


def test_format_context_delimiter():
    """Verify context formatting includes clean inline citation markers and delimiters without raw source tags."""
    docs = ["First document text", "Second document text"]
    metas = [
        {"risk_id": "LLM08:2026", "page": 47, "source": "owasp_llm_top10_2026", "source_title": "OWASP Top 10 for LLM Applications 2026"},
        {"risk_id": "", "page": 1, "source": "aegis", "source_title": "Aegis System Documentation"},
    ]
    formatted = AssistantRetriever.format_context(docs, metas)
    assert "[LLM08:2026, p.47]" in formatted
    assert "[Aegis System Documentation, p.1]" in formatted
    assert "---" in formatted
    # Must NOT contain leaking (source: ...)
    assert "(source: owasp_llm_top10_2026)" not in formatted
    assert "(source: aegis)" not in formatted


def test_clean_response_artifacts():
    """Verify clean_response strips trailing (source: ...) tags and leading citation blocks."""
    raw = "[LLM03:2026, p.24] (source: owasp_llm_top10_2026) and [LLM04:2026, p.28] (source: owasp_llm_top10_2026)\n\nExcessive Agency and Supply Chain are distinct categories [LLM03:2026, p.24] (source: aegis_plain_language).\n\nIn summary, while both represent distinct vulnerabilities..."
    cleaned = clean_response(raw)

    assert "(source: owasp_llm_top10_2026)" not in cleaned
    assert "(source: aegis_plain_language)" not in cleaned
    assert not cleaned.startswith("[LLM03:2026")
    assert cleaned.startswith("Excessive Agency and Supply Chain")
    assert "In summary, while both" not in cleaned


def test_deduplicate_citations_logic():
    """Verify deduplicate_citations removes identical chunk references and enriches provenance."""
    metas = [
        {"risk_id": "LLM04:2026", "page": 28, "section": "Description", "source": "owasp_llm_top10_2026", "chunk_id": "c1", "excerpt": "Excerpt 1"},
        {"risk_id": "LLM04:2026", "page": 28, "section": "Description", "source": "owasp_llm_top10_2026", "chunk_id": "c2", "excerpt": "Excerpt 2"},
        {"risk_id": "LLM03:2026", "page": 24, "section": "Description", "source": "owasp_llm_top10_2026", "chunk_id": "c3", "excerpt": "Excerpt 3"},
    ]
    deduped = deduplicate_citations(metas)
    assert len(deduped) == 2
    risk_ids = [c["risk_id"] for c in deduped]
    assert risk_ids == ["LLM04:2026", "LLM03:2026"]
    assert deduped[0]["source_title"] == "OWASP Top 10 for LLM Applications 2026"
    assert deduped[0]["excerpt"] == "Excerpt 1"


def test_scan_evidence_inquiry_detection():
    """Verify regex detects inquiries asking whether a scan confirmed a target vulnerability."""
    assert bool(SCAN_EVIDENCE_INQUIRY_RE.search("Was a vulnerability detected in my application?"))
    assert bool(SCAN_EVIDENCE_INQUIRY_RE.search("Did the scan find any prompt injection?"))
    assert bool(SCAN_EVIDENCE_INQUIRY_RE.search("Has my scan confirmed LLM08?"))
    assert bool(SCAN_EVIDENCE_INQUIRY_RE.search("Was LLM01 detected in the target?"))

    # Factual knowledge queries should NOT match
    assert not bool(SCAN_EVIDENCE_INQUIRY_RE.search("What is LLM01:2026 Prompt Injection?"))
    assert not bool(SCAN_EVIDENCE_INQUIRY_RE.search("How does Aegis test for LLM08?"))


def test_schemas_validation():
    """Verify Pydantic schemas validate required fields and default factories."""
    citation = CitationItem(
        source="owasp_llm_top10_2026",
        risk_id="LLM08:2026",
        page=47,
        chunk_id="chk-123",
        excerpt="Sample verified excerpt",
    )
    assert citation.page == 47
    assert citation.chunk_id == "chk-123"
    assert citation.excerpt == "Sample verified excerpt"

    msg = ChatMessage(role="assistant", text="Grounded reply", citations=[citation])
    assert len(msg.citations) == 1

    req = AssistantChatRequest(message="Test question")
    assert req.history == []
    assert req.mode is None

    resp = AssistantChatResponse(reply="Test reply", mode="ask")
    assert resp.source_ids == []
    assert resp.citations == []
