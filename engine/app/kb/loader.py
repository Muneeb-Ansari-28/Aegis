"""Knowledge Base JSON File Loader."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class KBLoader:
    """Utility class to load structured knowledge base assets."""

    @staticmethod
    def load_owasp(category: str, year: str = "2026") -> dict:
        kb_path = Path(__file__).parent / "01_OWASP" / year / f"{category}.json"
        if kb_path.exists():
            with open(kb_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        return {}

    @staticmethod
    def load_attack_technique(category: str) -> dict:
        cat_lower = category.lower()
        candidates = [
            Path(__file__).parent / "02_ATTACK_TECHNIQUES" / f"{cat_lower}_direct_disclosure.json",
            Path(__file__).parent / "02_ATTACK_TECHNIQUES" / f"{cat_lower}_prompt_injection.json",
            Path(__file__).parent / "02_ATTACK_TECHNIQUES" / f"{cat_lower}_excessive_agency.json",
            Path(__file__).parent / "02_ATTACK_TECHNIQUES" / f"{cat_lower}_vector_rag_leakage.json",
            Path(__file__).parent / "02_ATTACK_TECHNIQUES" / f"{cat_lower}_improper_output.json",
        ]
        for path in candidates:
            if path.exists():
                with open(path, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
        return {}

    @staticmethod
    def load_evaluation_rules(category: str) -> dict:
        cat_lower = category.lower()
        path = Path(__file__).parent / "05_EVALUATION_RULES" / f"{cat_lower}_rules.json"
        if path.exists():
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        return {}

    @staticmethod
    def load_risk_rules() -> dict:
        path = Path(__file__).parent / "06_RISK_RULES" / "risk_rules.json"
        if path.exists():
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        return {}

    @staticmethod
    def load_test_cases(category: Optional[str] = None) -> List[dict]:
        path = Path(__file__).parent / "04_TEST_CASES" / "test_cases.json"
        if path.exists():
            with open(path, "r", encoding="utf-8-sig") as f:
                cases = json.load(f)
            if category:
                return [c for c in cases if c.get("category") == category]
            return cases
        return []
