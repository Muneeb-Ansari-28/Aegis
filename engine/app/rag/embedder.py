"""Nomic Embed Text Client."""
class NomicEmbedder:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Returns embeddings
        return [[0.0] * 768 for _ in texts]
