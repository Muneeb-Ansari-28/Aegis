r"""User Data and OS Path Resolution (%APPDATA%\Aegis)."""
import os
from pathlib import Path

def get_app_data_dir() -> Path:
    app_data = os.getenv("APPDATA")
    if app_data:
        base = Path(app_data) / "Aegis"
    else:
        base = Path.home() / ".aegis"
    return base

def ensure_app_dirs() -> None:
    base = get_app_data_dir()
    for sub in ["db", "chroma", "reports", "profiles", "logs"]:
        (base / sub).mkdir(parents=True, exist_ok=True)
