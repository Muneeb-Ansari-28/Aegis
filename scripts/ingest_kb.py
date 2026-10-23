"""Ingest Aegis Knowledge Base into local ChromaDB with deterministic IDs."""
import asyncio
import logging
from pathlib import Path
import sys

# Ensure engine is on sys.path
engine_path = Path(__file__).resolve().parent.parent / "engine"
if str(engine_path) not in sys.path:
    sys.path.insert(0, str(engine_path))

from app.rag.indexer import index_knowledge_base
from app.rag.vector_store import VectorStore
from app.rag.embedder import NomicEmbedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ingest_kb")


async def main() -> None:
    """Run knowledge base ingestion pipeline."""
    logger.info("Starting Aegis Knowledge Base ingestion...")
    knowledge_dir = engine_path / "knowledge"
    vector_store = VectorStore()
    embedder = NomicEmbedder()

    count = await index_knowledge_base(
        vector_store=vector_store,
        embedder=embedder,
        knowledge_dir=knowledge_dir,
    )
    logger.info(f"Ingestion complete: {count} chunks indexed in ChromaDB collection '{vector_store.collection_name}'.")
    logger.info(f"Verified total documents in store: {vector_store.count()}")


if __name__ == "__main__":
    asyncio.run(main())
