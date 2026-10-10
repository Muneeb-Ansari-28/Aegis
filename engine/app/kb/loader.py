"""Knowledge Base JSON File Loader."""
import json
from pathlib import Path

class KBLoader:
    @staticmethod
    def load_owasp(category: str, year: str = "2025") -> dict:
        kb_path = Path(__file__).parent / "01_OWASP" / year / f"{category}.json"
        if kb_path.exists():
            with open(kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
