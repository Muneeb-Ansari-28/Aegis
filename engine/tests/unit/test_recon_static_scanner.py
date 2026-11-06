"""Unit tests for Tier 3 Static Project Scanner and Privacy Guard."""
import pytest
from app.recon.static_scanner import StaticProjectScanner


def test_static_scanner_detects_requirements_and_frameworks(tmp_path):
    # Setup mock project folder
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("fastapi>=0.100.0\nchromadb==0.4.24\nlangchain>=0.1.0\nuvicorn\n")

    env_file = tmp_path / ".env"
    env_file.write_text(
        "PINECONE_API_KEY=super_secret_actual_key_12345\n"
        "CHROMA_HOST=localhost\n"
        "DATABASE_PASSWORD=dont_leak_this_password\n"
    )

    py_file = tmp_path / "app.py"
    py_file.write_text(
        "from fastapi import FastAPI\n"
        "import chromadb\n"
        "from langchain.chains import RetrievalQA\n"
        "app = FastAPI()\n"
    )

    scanner = StaticProjectScanner(str(tmp_path))
    result = scanner.scan()

    assert result.has_rag is True
    assert result.has_vector_db is True
    assert any("ChromaDB" in v for v in result.vector_db_names)
    assert any("LangChain" in f for f in result.detected_frameworks)

    # Privacy verification: key names MUST be present, but values MUST NEVER appear in evidence or keys!
    assert "PINECONE_API_KEY" in result.detected_env_keys
    assert "DATABASE_PASSWORD" in result.detected_env_keys
    for ev in result.evidence:
        assert "super_secret_actual_key_12345" not in ev
        assert "dont_leak_this_password" not in ev


def test_static_scanner_handles_empty_or_nonexistent_dir(tmp_path):
    nonexistent = tmp_path / "does_not_exist_12345"
    scanner = StaticProjectScanner(str(nonexistent))
    result = scanner.scan()
    assert result.has_rag is False
    assert result.has_vector_db is False
    assert len(result.evidence) > 0

