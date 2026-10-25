"""Knowledge Base Markdown parser and vector indexer."""
import hashlib
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from app.rag.embedder import NomicEmbedder
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

PAGE_RE = re.compile(r"^###\s+Source page\s+(\d+)\s*$")
RISK_HEADER_RE = re.compile(r"^##\s+(LLM\d\d:2026)\s+(.+)$")
SECTION_HEADER_RE = re.compile(r"^####?\s+(.+)$")
SIMPLE_EXPLANATION_RE = re.compile(r"^(LLM\d\d:2026)\s+(.+?)\s*---\s*simple explanation$")


def generate_chunk_id(source: str, risk_id: str, section: str, index: int, text: str) -> str:
    """
    Generate a deterministic, idempotent chunk ID.

    Args:
        source: Source tag (e.g. owasp_llm_top10_2026, aegis).
        risk_id: Risk ID (e.g. LLM08:2026) or empty string.
        section: Section name.
        index: Index within section.
        text: Normalized chunk text.

    Returns:
        Deterministic chunk ID string.
    """
    norm_text = " ".join(text.split())
    raw = f"{source}|{risk_id}|{section}|{index}|{norm_text}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    clean_risk = risk_id.replace(":", "_").replace(" ", "_") if risk_id else "general"
    clean_sec = re.sub(r"[^a-zA-Z0-9_]", "_", section.lower())[:24]
    return f"{source}-{clean_risk}-{clean_sec}-{index}-{digest}"


def split_into_chunks(text: str, max_words: int = 300, overlap: int = 30) -> List[str]:
    """
    Split a long section into coherent word chunks with slight overlap.

    Args:
        text: Full text of the section.
        max_words: Maximum words per chunk.
        overlap: Overlap word count between consecutive chunks.

    Returns:
        List of chunk text strings.
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= max_words:
        return [text.strip()]

    chunks: List[str] = []
    step = max(max_words - overlap, 50)
    for i in range(0, len(words), step):
        piece = " ".join(words[i : i + max_words])
        if piece.strip():
            chunks.append(piece.strip())
        if i + max_words >= len(words):
            break
    return chunks


def parse_owasp_markdown(path: Path) -> List[Tuple[str, str, Dict[str, Any]]]:
    """
    Parse curated OWASP Top 10 2026 Markdown into structured semantic chunks with page numbers.

    Args:
        path: Path to OWASP-LLM-Top-10-2026.md.

    Returns:
        List of tuples: (chunk_id, chunk_text, metadata).
    """
    if not path.exists():
        logger.warning(f"OWASP knowledge file not found at: {path}")
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    chunks: List[Tuple[str, str, Dict[str, Any]]] = []

    current_page: int = 10
    current_risk_id: str = ""
    current_risk_name: str = ""
    current_section: str = "Overview"
    current_source: str = "owasp_llm_top10_2026"
    current_level: str = "technical"
    is_simple_section: bool = False

    buffer: List[str] = []

    def flush_section() -> None:
        nonlocal buffer, chunks
        content = "\n".join(buffer).strip()
        buffer.clear()
        if not content:
            return

        word_chunks = split_into_chunks(content, max_words=320, overlap=30)
        for idx, piece in enumerate(word_chunks):
            # Create clear prefix header
            if current_risk_id:
                header = f"{current_risk_id} {current_risk_name} — {current_section}\n\n"
            else:
                header = f"{current_section}\n\n"

            chunk_text = header + piece
            meta = {
                "source": current_source,
                "source_title": "OWASP Top 10 for LLM Applications 2026",
                "risk_id": current_risk_id,
                "risk_name": current_risk_name,
                "section": current_section,
                "page": current_page,
                "level": current_level,
                "chunk_index": idx,
                "path": path.as_posix(),
            }
            c_id = generate_chunk_id(current_source, current_risk_id, current_section, idx, piece)
            chunks.append((c_id, chunk_text, meta))

    for line in lines:
        # Check for page marker
        m_page = PAGE_RE.match(line)
        if m_page:
            current_page = int(m_page.group(1))
            continue

        # Check for main risk header: ## LLMxx:2026 ...
        m_risk = RISK_HEADER_RE.match(line)
        if m_risk:
            flush_section()
            risk_id = m_risk.group(1)
            raw_title = m_risk.group(2).strip()

            m_simple = SIMPLE_EXPLANATION_RE.match(f"{risk_id} {raw_title}")
            if m_simple or "simple explanation" in raw_title.lower():
                is_simple_section = True
                current_risk_id = risk_id
                current_risk_name = raw_title.split("---")[0].strip()
                current_section = "Simple Explanation"
                current_source = "owasp_llm_top10_2026"
                current_level = "simple"
            else:
                is_simple_section = False
                current_risk_id = risk_id
                current_risk_name = raw_title
                current_section = "Overview"
                current_source = "owasp_llm_top10_2026"
                current_level = "technical"
            continue

        # Check for section header: ### ... or #### ...
        m_sec = SECTION_HEADER_RE.match(line)
        if m_sec:
            sec_title = m_sec.group(1).strip()
            # Check if this is a simple explanation header under ###
            if "simple explanation" in sec_title.lower():
                flush_section()
                is_simple_section = True
                for rid in [f"LLM{i:02d}:2026" for i in range(1, 11)]:
                    if rid in sec_title:
                        current_risk_id = rid
                        break
                current_risk_name = sec_title.split("---")[0].strip()
                current_section = "Simple Explanation"
                current_source = "owasp_llm_top10_2026"
                current_level = "simple"
                continue

            if not is_simple_section and line.startswith("####"):
                flush_section()
                current_section = sec_title
                continue

            if line.startswith("## ") and "quick reference" in line.lower():
                flush_section()
                current_risk_id = ""
                current_risk_name = "2026 Top 10 Quick Reference & Crosswalk"
                current_section = "Crosswalk"
                current_source = "owasp_llm_top10_2026"
                current_level = "standard"
                continue

            if line.startswith("## ") and "glossary" in line.lower():
                flush_section()
                current_risk_id = ""
                current_risk_name = "Glossary"
                current_section = "Glossary"
                current_source = "owasp_llm_top10_2026"
                current_level = "simple"
                continue

        buffer.append(line)

    flush_section()
    return chunks


def parse_aegis_markdown(path: Path) -> List[Tuple[str, str, Dict[str, Any]]]:
    """
    Parse verified Aegis documentation Markdown files into chunks.

    Args:
        path: Path to Aegis markdown file.

    Returns:
        List of tuples: (chunk_id, chunk_text, metadata).
    """
    if not path.exists():
        logger.warning(f"Aegis knowledge file not found at: {path}")
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    chunks: List[Tuple[str, str, Dict[str, Any]]] = []

    doc_title = path.stem.replace("_", " ").title()
    current_section = "Overview"
    buffer: List[str] = []

    def flush_section() -> None:
        nonlocal buffer, chunks
        content = "\n".join(buffer).strip()
        buffer.clear()
        if not content:
            return

        word_chunks = split_into_chunks(content, max_words=300, overlap=25)
        for idx, piece in enumerate(word_chunks):
            header = f"Aegis Documentation — {doc_title} ({current_section})\n\n"
            chunk_text = header + piece
            meta = {
                "source": "aegis",
                "source_title": f"Aegis System Documentation — {doc_title}",
                "risk_id": "",
                "risk_name": "",
                "section": current_section,
                "page": 1,
                "level": "standard",
                "chunk_index": idx,
                "path": path.as_posix(),
            }
            c_id = generate_chunk_id("aegis", path.stem, current_section, idx, piece)
            chunks.append((c_id, chunk_text, meta))

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            doc_title = line.replace("# ", "").strip()
            continue

        if line.startswith("## ") or line.startswith("### "):
            flush_section()
            current_section = line.lstrip("#").strip()
            continue

        buffer.append(line)

    flush_section()
    return chunks


def load_all_knowledge_chunks(knowledge_dir: Path) -> List[Tuple[str, str, Dict[str, Any]]]:
    """
    Discover and parse all knowledge base Markdown documents.

    Args:
        knowledge_dir: Path to engine/knowledge directory.

    Returns:
        List of all (chunk_id, chunk_text, metadata) tuples.
    """
    all_chunks: List[Tuple[str, str, Dict[str, Any]]] = []

    # 1. Parse OWASP Top 10 2026
    owasp_file = knowledge_dir / "owasp" / "OWASP-LLM-Top-10-2026.md"
    if owasp_file.exists():
        owasp_chunks = parse_owasp_markdown(owasp_file)
        logger.info(f"Parsed {len(owasp_chunks)} chunks from OWASP knowledge file.")
        all_chunks.extend(owasp_chunks)
    else:
        logger.warning(f"OWASP file not found at: {owasp_file}")

    # 2. Parse Aegis product docs
    aegis_dir = knowledge_dir / "aegis"
    if aegis_dir.exists():
        for aegis_md in sorted(aegis_dir.glob("*.md")):
            aegis_chunks = parse_aegis_markdown(aegis_md)
            logger.info(f"Parsed {len(aegis_chunks)} chunks from {aegis_md.name}.")
            all_chunks.extend(aegis_chunks)

    return all_chunks


async def index_knowledge_base(
    vector_store: Optional[VectorStore] = None,
    embedder: Optional[NomicEmbedder] = None,
    knowledge_dir: Optional[Path] = None,
) -> int:
    """
    Index all knowledge documents into ChromaDB with deterministic IDs.

    Args:
        vector_store: Optional VectorStore instance.
        embedder: Optional NomicEmbedder instance.
        knowledge_dir: Path to knowledge directory.

    Returns:
        Count of indexed chunks.
    """
    if vector_store is None:
        vector_store = VectorStore()
    if embedder is None:
        embedder = NomicEmbedder()
    if knowledge_dir is None:
        # Resolve to engine/knowledge
        knowledge_dir = Path(__file__).resolve().parent.parent.parent / "knowledge"

    chunks = load_all_knowledge_chunks(knowledge_dir)
    if not chunks:
        logger.warning("No knowledge chunks found to index.")
        return 0

    ids = [c[0] for c in chunks]
    docs = [c[1] for c in chunks]
    metas = [c[2] for c in chunks]

    logger.info(f"Embedding {len(docs)} knowledge chunks using NomicEmbedder...")
    embeddings = await embedder.embed_documents(docs)

    logger.info(f"Upserting {len(ids)} chunks into ChromaDB collection '{vector_store.collection_name}'...")
    vector_store.upsert_documents(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metas,
    )

    logger.info(f"Successfully indexed {len(ids)} chunks. Total in collection: {vector_store.count()}")
    return len(ids)
