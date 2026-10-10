"""Engine & Ollama Readiness Health Check."""
from fastapi import APIRouter
import httpx
from app.core.config import get_settings

router = APIRouter()

@router.get("")
async def get_health():
    settings = get_settings()
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/version")
            ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False

    return {
        "status": "online",
        "engine_version": "0.1.0",
        "ollama_connected": ollama_ok,
    }
