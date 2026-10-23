"""Retrieval module for Aegis RAG Assistant and Knowledge Base."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import get_settings
from app.rag.embedder import NomicEmbedder
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class AssistantRetriever:
    """Retrieves relevant knowledge chunks for the Aegis AI Assistant."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[NomicEmbedder] = None,
    ) -> None:
        """Initialize retriever with vector store and embedder."""
        self.settings = get_settings()
        self.store = vector_store or VectorStore()
        self.embedder = embedder or NomicEmbedder()

    async def retrieve(
        self,
        query: str,
        n_results: int = 5,
        relevance_cutoff: Optional[float] = None,
    ) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Embed the query and retrieve relevant chunks below the cosine distance cutoff.

        Args:
            query: User search query string.
            n_results: Maximum results to retrieve.
            relevance_cutoff: Maximum acceptable cosine distance.

        Returns:
            Tuple of (kept_documents, kept_metadatas, kept_ids).
        """
        cutoff = relevance_cutoff if relevance_cutoff is not None else self.settings.RAG_RELEVANCE_CUTOFF
        try:
            vec = await self.embedder.embed_query(query)
            res = self.store.query(vec, n_results=n_results)
        except Exception as e:
            logger.error(f"Vector search failed for query '{query}': {e}")
            return [], [], []

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        ids = res.get("ids", [[]])[0]
        dists = res.get("distances", [[]])[0]

        kept_docs: List[str] = []
        kept_metas: List[Dict[str, Any]] = []
        kept_ids: List[str] = []

        for d, m, i, dist in zip(docs, metas, ids, dists):
            if dist <= cutoff:
                kept_docs.append(d)
                kept_metas.append(m)
                kept_ids.append(i)

        return kept_docs, kept_metas, kept_ids

    @staticmethod
    def format_context(documents: List[str], metadatas: List[Dict[str, Any]]) -> str:
        """
        Format retrieved document chunks with citation markers into a single string.

        Args:
            documents: List of chunk text passages.
            metadatas: List of chunk metadata dictionaries.

        Returns:
            Formatted context string.
        """
        formatted_chunks: List[str] = []
        for doc, meta in zip(documents, metadatas):
            risk_id = meta.get("risk_id", "")
            page = meta.get("page", 1)
            source = meta.get("source", "aegis")
            header = f"[{risk_id if risk_id else 'Aegis Documentation'}, p.{page}] (source: {source})"
            formatted_chunks.append(f"{header}\n{doc}")

        return "\n\n---\n\n".join(formatted_chunks)


class KBRetriever:
    """Attack path vs evaluation path retriever (backward compatible)."""

    async def retrieve_seeds(self, category: str) -> List[str]:
        """Retrieve seed prompts for a given vulnerability category."""
        return []
