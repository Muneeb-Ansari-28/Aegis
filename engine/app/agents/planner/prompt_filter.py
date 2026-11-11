"""Prompt Library Metadata Filter for the Deterministic Test Planner."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.recon.schemas import TargetProfile

logger = logging.getLogger(__name__)

# The currently implemented LLM08 evaluator supports direct disclosure requests.
# More aggressive techniques remain unavailable until separately designed and reviewed.
_ALLOWED_TECHNIQUES = {
    "LLM08": {"direct_disclosure_request"},
}

KB_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "kb" / "03_PROMPT_LIBRARY"


class PromptMetadataFilter:
    """
    Evaluates 'requires' and 'applicable_when' expressions on prompt records
    against a TargetProfile to return applicable prompt IDs.
    """

    @classmethod
    def get_applicable_prompts(
        cls,
        category: str,
        profile: TargetProfile,
        library_root: Optional[Path] = None,
    ) -> List[str]:
        """
        Scan prompt library subdirectories (fixed, templates, variations) for prompts
        matching the specified category and satisfying profile prerequisites.
        """
        root = library_root or KB_PROMPTS_ROOT
        applicable_ids: List[str] = []
        target_cat = (category or "").upper()

        if not root.exists():
            return applicable_ids

        # Look in all JSON files under fixed/, templates/, variations/
        for json_path in sorted(root.glob("**/*.json")):
            try:
                with open(json_path, "r", encoding="utf-8-sig") as f:
                    records = json.load(f)
                if not isinstance(records, list):
                    continue

                for prompt_record in records:
                    if not isinstance(prompt_record, dict):
                        continue

                    record_cat = prompt_record.get("category", "")
                    prompt_id = prompt_record.get("id") or prompt_record.get("prompt_id")
                    if not prompt_id:
                        continue

                    # Category resolution with canonical 2026 / legacy 2025 support:
                    # In 2026, LLM08 is Hidden Context Exposure (former LLM07 system prompt leakage).
                    # Allow LLM08 to match LLM08 records and legacy LLM07 direct disclosure records.
                    rec_cat_upper = record_cat.upper() if record_cat else ""
                    id_upper = str(prompt_id).upper()

                    matches_category = False
                    if target_cat == "LLM08":
                        if rec_cat_upper in ("LLM08", "LLM07") or id_upper.startswith(("LLM08", "LLM07")):
                            matches_category = True
                    elif target_cat == "LLM09":
                        if rec_cat_upper == "LLM09" or id_upper.startswith("LLM09"):
                            matches_category = True
                    else:
                        if rec_cat_upper:
                            matches_category = (rec_cat_upper == target_cat)
                        else:
                            matches_category = id_upper.startswith(target_cat)

                    if not matches_category:
                        continue

                    allowed_techniques = _ALLOWED_TECHNIQUES.get(target_cat)
                    technique = prompt_record.get("technique")
                    if allowed_techniques is not None and technique not in allowed_techniques:
                        continue

                    # Evaluate 'requires' rules
                    requires = prompt_record.get("requires", {})
                    if not cls._matches_requires(requires, profile):
                        continue

                    # Evaluate 'applicable_when' expressions
                    applicable_when = prompt_record.get("applicable_when")
                    if not cls._matches_applicable_when(applicable_when, profile):
                        continue

                    if prompt_id not in applicable_ids:
                        applicable_ids.append(prompt_id)
            except Exception as e:
                logger.debug(f"Error reading prompts from {json_path}: {e}")

        return applicable_ids

    @staticmethod
    def _matches_requires(requires: Dict[str, Any], profile: TargetProfile) -> bool:
        """
        Check if target profile satisfies prompt requirements.
        If a requirement is null/omitted, it matches any profile.
        """
        if not requires:
            return True

        if "has_rag" in requires and requires["has_rag"] is not None:
            if profile.has_rag.detected != requires["has_rag"]:
                return False

        if "has_tools" in requires and requires["has_tools"] is not None:
            if profile.has_tools.detected != requires["has_tools"]:
                return False

        if "memory" in requires and requires["memory"] is not None:
            if profile.has_conversation_memory.detected != requires["memory"]:
                return False

        if "renders_html" in requires and requires["renders_html"] is not None:
            if profile.renders_html.detected != requires["renders_html"]:
                return False

        return True

    @staticmethod
    def _matches_applicable_when(expr: Any, profile: TargetProfile) -> bool:
        """
        Evaluate boolean string expressions in 'applicable_when'.
        Supports 'true', 'false', 'has_rag', 'not has_rag', 'has_tools', 'renders_html', 'memory'.
        """
        if expr is None:
            return True
        if isinstance(expr, bool):
            return expr
        if not isinstance(expr, str):
            return True

        cleaned = expr.strip().lower()
        if cleaned in ("true", "1", "always", ""):
            return True
        if cleaned in ("false", "0", "never"):
            return False

        if cleaned in ("has_rag", "rag"):
            return bool(profile.has_rag.detected)
        if cleaned in ("not has_rag", "!has_rag", "no_rag"):
            return not bool(profile.has_rag.detected)

        if cleaned in ("has_tools", "tools"):
            return bool(profile.has_tools.detected)
        if cleaned in ("not has_tools", "!has_tools", "no_tools"):
            return not bool(profile.has_tools.detected)

        if cleaned in ("renders_html", "html"):
            return bool(profile.renders_html.detected)

        if cleaned in ("memory", "has_memory"):
            return bool(profile.has_conversation_memory.detected)

        return True
