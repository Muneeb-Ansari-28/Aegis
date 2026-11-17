"""Aegis Engine Configuration Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.paths import get_app_data_dir


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
    MODEL_BASE: str = "hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF:Q4_K_M"
    MODEL_ATTACK: str = "hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF:Q4_K_M"
    MODEL_JUDGE: str = "hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF:Q4_K_M"
    MODEL_RECON: str = "hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF:Q4_K_M"
    MODEL_TRIAGE: str = "llama-guard3:1b"
    MODEL_EMBED: str = "nomic-embed-text:latest"
    MODEL_ASSISTANT: str = "hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF:Q4_K_M"

    # RAG Assistant Settings
    RAG_TOP_K: int = 5
    RAG_RELEVANCE_CUTOFF: float = 0.50

    # Playwright Settings
    PLAYWRIGHT_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000

    # Scan Control Budgets
    MAX_ATTEMPTS_PER_CATEGORY: int = 10

    # Database
    DATABASE_URL: str = f"sqlite:///{(get_app_data_dir() / 'db' / 'aegis.db').as_posix()}"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
