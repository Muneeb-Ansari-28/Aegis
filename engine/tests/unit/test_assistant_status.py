"""Unit tests for Assistant status endpoint and Ollama model readiness."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.api.v1.router import app
from app.llm.ollama_client import OllamaClient
from app.core.api_auth import get_api_token


def make_client():
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={
            "Authorization": f"Bearer {get_api_token()}",
            "Origin": "http://localhost:5173",
        },
    )


@pytest.mark.asyncio
async def test_ollama_client_has_model():
    client = OllamaClient()
    with patch.object(client, "list_models", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ["llama3.2:latest", "nomic-embed-text:latest"]

        assert await client.has_model("llama3.2:latest") is True
        assert await client.has_model("llama3.2") is True
        assert await client.has_model("LLAMA3.2:LATEST") is True
        assert await client.has_model("nomic-embed-text") is True
        assert await client.has_model("nonexistent-model") is False


@pytest.mark.asyncio
async def test_assistant_status_ollama_offline():
    async with make_client() as client:
        with patch("app.api.v1.assistant.OllamaClient.is_available", new_callable=AsyncMock) as mock_avail, \
             patch("app.api.v1.assistant.VectorStore.count", return_value=50):
            mock_avail.return_value = False

            resp = await client.get("/api/v1/assistant/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["ollama_available"] is False
            assert data["model_available"] is False


@pytest.mark.asyncio
async def test_assistant_status_model_missing():
    async with make_client() as client:
        with patch("app.api.v1.assistant.OllamaClient.is_available", new_callable=AsyncMock) as mock_avail, \
             patch("app.api.v1.assistant.OllamaClient.has_model", new_callable=AsyncMock) as mock_model, \
             patch("app.api.v1.assistant.VectorStore.count", return_value=50):
            mock_avail.return_value = True
            mock_model.return_value = False

            resp = await client.get("/api/v1/assistant/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["ollama_available"] is True
            assert data["model_available"] is False


@pytest.mark.asyncio
async def test_assistant_status_kb_empty():
    async with make_client() as client:
        with patch("app.api.v1.assistant.OllamaClient.is_available", new_callable=AsyncMock) as mock_avail, \
             patch("app.api.v1.assistant.OllamaClient.has_model", new_callable=AsyncMock) as mock_model, \
             patch("app.api.v1.assistant.VectorStore.count", return_value=0):
            mock_avail.return_value = True
            mock_model.return_value = True

            resp = await client.get("/api/v1/assistant/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["ollama_available"] is True
            assert data["model_available"] is True
            assert data["kb_chunks_indexed"] == 0


@pytest.mark.asyncio
async def test_assistant_status_fully_ready():
    async with make_client() as client:
        with patch("app.api.v1.assistant.OllamaClient.is_available", new_callable=AsyncMock) as mock_avail, \
             patch("app.api.v1.assistant.OllamaClient.has_model", new_callable=AsyncMock) as mock_model, \
             patch("app.api.v1.assistant.VectorStore.count", return_value=115):
            mock_avail.return_value = True
            mock_model.return_value = True

            resp = await client.get("/api/v1/assistant/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ready"
            assert data["ollama_available"] is True
            assert data["model_available"] is True
            assert data["kb_chunks_indexed"] == 115

