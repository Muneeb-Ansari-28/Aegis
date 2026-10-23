"""Nomic Embed Text client adapter over local Ollama."""
from typing import List
from app.core.config import get_settings
from app.llm.ollama_client import OllamaClient

DOC_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
BATCH_SIZE = 25


class NomicEmbedder:
    """Nomic text embedder using local Ollama model."""

    def __init__(self) -> None:
        """Initialize the embedder with settings and Ollama client."""
        self.settings = get_settings()
        self.client = OllamaClient()

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of document passages using the search_document: prefix in batches.

        Args:
            texts: List of raw text chunks to embed.

        Returns:
            List of 768-dimensional float embedding vectors.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            prefixed = [DOC_PREFIX + t for t in batch]
            embeddings = await self.client.embed(
                model=self.settings.MODEL_EMBED,
                inputs=prefixed,
            )
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single search query using the search_query: prefix.

        Args:
            text: Query string.

        Returns:
            Single 768-dimensional float embedding vector.
        """
        res = await self.client.embed(
            model=self.settings.MODEL_EMBED,
            inputs=[QUERY_PREFIX + text],
        )
        if not res:
            return [0.0] * 768
        return res[0]

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Backward-compatible embed call for raw documents."""
        return await self.embed_documents(texts)
