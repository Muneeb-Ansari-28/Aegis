"""Rebuild ChromaDB Vector Index from Knowledge Base Markdown files."""
import asyncio
from pathlib import Path
import sys

engine_path = Path(__file__).resolve().parent.parent / "engine"
if str(engine_path) not in sys.path:
    sys.path.insert(0, str(engine_path))

from app.rag.indexer import index_knowledge_base


def main() -> None:
    """Rebuild KB vector index."""
    asyncio.run(index_knowledge_base())


if __name__ == "__main__":
    main()
