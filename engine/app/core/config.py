"""Aegis Engine Configuration Settings."""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    DEBUG: bool = True
    
    # Ollama Endpoints & Models
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_ATTACK: str = "qwen2.5:3b"
    MODEL_JUDGE: str = "qwen2.5:3b"
    MODEL_TRIAGE: str = "llama-guard3:1b"
    MODEL_EMBED: str = "nomic-embed-text:v1.5"

    # Playwright Settings
    PLAYWRIGHT_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000

    # Scan Control Budgets
    MAX_ATTEMPTS_PER_CATEGORY: int = 10

    # Database
    DATABASE_URL: str = "sqlite:///./aegis.db"

    class Config:
        env_file = ".env"
        extra = "allow"

_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
