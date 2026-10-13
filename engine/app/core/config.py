"""Aegis Engine Configuration Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        extra="allow",
    )

    HOST: str = "127.0.0.1"
    PORT: int = 8765
    DEBUG: bool = True

    # Ollama Endpoints & Models
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_ATTACK: str = "llama3.2:latest"
    MODEL_JUDGE: str = "llama3.2:latest"
    MODEL_TRIAGE: str = "llama3.2:latest"
    MODEL_EMBED: str = "nomic-embed-text:v1.5"

    # Playwright Settings
    PLAYWRIGHT_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000

    # Scan Control Budgets
    MAX_ATTEMPTS_PER_CATEGORY: int = 10

    # Database
    DATABASE_URL: str = "sqlite:///./aegis.db"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
