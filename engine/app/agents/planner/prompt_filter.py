"""Prompt Library Metadata Filter for the Deterministic Test Planner."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.recon.schemas import TargetProfile

logger = logging.getLogger(__name__)

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
        Scan prompt library subdirectories (fixed, templates, adaptive) for prompts
        matching the specified category and satisfying profile prerequisites.
        """
        root = library_root or KB_PROMPTS_ROOT
        applicable_ids: List[str] = []

        if not root.exists():
            return applicable_ids

        # Look in all JSON files under fixed/, templates/, variations/
        for json_path in root.glob("**/*.json"):
            try:
                with open(json_path, "r", encoding="utf-8-sig") as f:
                    records = json.load(f)
                if not isinstance(records, list):
                    continue

                for prompt_record in records:
                    if not isinstance(prompt_record, dict):
                        continue
                    # Match category (e.g. LLM01, LLM07, LLM08)
                    record_cat = prompt_record.get("category", "")
                    prompt_id = prompt_record.get("id") or prompt_record.get("prompt_id")
                    if not prompt_id:
                        continue

                    # If record specifies category, check equality; if not specified, check ID prefix
                    if record_cat:
                        if record_cat.upper() != category.upper():
                            continue
                    else:
                        if not prompt_id.upper().startswith(category.upper()):
                            continue

                    # Evaluate 'requires' rules
                    requires = prompt_record.get("requires", {})
                    if not cls._matches_requires(requires, profile):
                        continue

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

