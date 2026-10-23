"""Ollama Unified LLM Wrapper Client."""
from typing import Any, List, Optional
import httpx
from app.core.config import get_settings


class OllamaClient:
    """Wrapper client for interacting with the local Ollama daemon."""

    def __init__(self) -> None:
        """Initialize the Ollama client with application settings."""
        self.settings = get_settings()

    async def is_available(self) -> bool:
        """
        Check if the local Ollama server is running and reachable.

        Returns:
            True if Ollama responds to health/version check, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.settings.OLLAMA_BASE_URL}/api/version")
                return resp.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate text completion from Ollama.

        Args:
            model: Name of the Ollama model (e.g. llama3.2:latest).
            prompt: User prompt text.
            system: Optional system instruction prompt.
            temperature: Sampling temperature (e.g. 0.2 for deterministic output).

        Returns:
            Model response string.

        Raises:
            httpx.HTTPError: If the HTTP request fails.
        """
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        if temperature is not None:
            payload["options"] = {"temperature": temperature}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def embed(self, model: str, inputs: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for a list of input texts.

        Args:
            model: Name of the embedding model (e.g. nomic-embed-text:latest).
            inputs: List of strings to embed.

        Returns:
            List of embedding vectors (list of floats).

        Raises:
            httpx.HTTPError: If the HTTP request fails.
        """
        if not inputs:
            return []

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.settings.OLLAMA_BASE_URL}/api/embed",
                json={"model": model, "input": inputs},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embeddings", [])
