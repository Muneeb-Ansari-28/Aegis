"""Knowledge Base JSON File Loader."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DuplicatePromptIdError(ValueError):
    """Raised when two KB records claim the same prompt ID."""


class KBLoader:
    """Utility class to load structured knowledge base assets."""

    @classmethod
    def get_prompt_library_dir(cls) -> Path:
        """Resolve path to prompt library directory."""
        return Path(__file__).parent / "03_PROMPT_LIBRARY"

    @classmethod
    def load_prompt_library(cls, kb_dir: Optional[Path] = None) -> Dict[str, dict]:
        """
        Load all prompt definitions from the prompt library.
        Returns a dict mapping prompt_id -> {
            "id": prompt_id,
            "category": category,
            "prompt": resolved_text,
            "raw": record,
        }
        """
        library_dir = kb_dir or cls.get_prompt_library_dir()
        prompts: Dict[str, dict] = {}
        if not library_dir.exists():
            return prompts

        for file_path in sorted(library_dir.glob("**/*.json")):
            try:
                content = file_path.read_text(encoding="utf-8-sig")
                data = json.loads(content)
                records = data if isinstance(data, list) else (data.get("prompts") if isinstance(data, dict) and isinstance(data.get("prompts"), list) else None)
                if records is None:
                    continue
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    prompt_id = record.get("id") or record.get("prompt_id")
                    if not isinstance(prompt_id, str) or not prompt_id.strip():
                        continue
                    prompt_id = prompt_id.strip()

                    if prompt_id in prompts:
                        raise DuplicatePromptIdError(f"Duplicate prompt ID '{prompt_id}' in prompt library.")

                    text = record.get("prompt")
                    if not isinstance(text, str) or not text.strip():
                        template_text = record.get("template")
                        if isinstance(template_text, str) and template_text.strip():
                            text = template_text
                            variables = record.get("variables")
                            if isinstance(variables, dict):
                                for key, value in variables.items():
                                    text = text.replace(f"{{{key}}}", str(value))
                    if isinstance(text, str) and text.strip():
                        category = record.get("category")
                        prompts[prompt_id] = {
                            "id": prompt_id,
                            "category": str(category).upper().strip() if category else None,
                            "prompt": text.strip(),
                            "raw": record,
                        }
            except DuplicatePromptIdError:
                raise
            except Exception as exc:
                logger.warning("Failed to read prompt library file %s: %s", file_path.name, exc)
        return prompts

    @classmethod
    def _matches_category(cls, record_cat: Optional[str], prompt_id: str, target_cat: str) -> bool:
        """Check category matching with support for canonical OWASP 2026 remappings."""
        target = target_cat.upper().strip()
        rec = record_cat.upper().strip() if record_cat else ""
        pid = prompt_id.upper().strip()
        if target == "LLM08":
            return rec in ("LLM08", "LLM07") or pid.startswith(("LLM08", "LLM07"))
        if target == "LLM09":
            return rec == "LLM09" or pid.startswith("LLM09")
        if rec:
            return rec == target
        return pid.startswith(target)

    @classmethod
    def load_prompts_by_ids(
        cls,
        prompt_ids: List[str],
        category: Optional[str] = None,
        kb_dir: Optional[Path] = None,
    ) -> Dict[str, str]:
        """
        Resolve prompt texts for the requested prompt IDs.
        Validates record shape, prompt IDs, and variable substitutions.
        If category is specified, verifies that loaded prompts belong to that category.
        Returns a dict mapping prompt_id -> resolved prompt text.
        """
        library = cls.load_prompt_library(kb_dir=kb_dir)
        result: Dict[str, str] = {}
        target_cat = category.upper().strip() if category else None

        for pid in prompt_ids:
            if not isinstance(pid, str):
                continue
            item = library.get(pid.strip())
            if item is None:
                continue
            if target_cat and not cls._matches_category(item.get("category"), pid, target_cat):
                logger.warning(
                    "Prompt %s category %s does not match requested %s",
                    pid,
                    item.get("category"),
                    target_cat,
                )
                continue
            result[pid] = item["prompt"]
        return result

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
