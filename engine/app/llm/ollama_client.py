"""Ollama Unified LLM Wrapper Client."""
import httpx
from app.core.config import get_settings

class OllamaClient:
    def __init__(self):
        self.settings = get_settings()

    async def generate(self, model: str, prompt: str, system: str = "") -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": model, "prompt": prompt, "system": system, "stream": False}
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
