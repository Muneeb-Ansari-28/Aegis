"""Parse Guard for Strict JSON Extraction from Model Outputs."""
import json
import logging
import re
from typing import List, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


def extract_json_candidates(text: str) -> List[str]:
    """
    Extract candidate JSON strings from raw text without greedily swallowing unrelated braces.
    Prioritizes markdown code blocks, then balanced curly brace spans.
    """
    candidates: List[str] = []

    # 1. Markdown code blocks (```json ... ``` or ``` ... ```)
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    for m in fence_pattern.finditer(text):
        content = m.group(1).strip()
        if content:
            candidates.append(content)

    # 2. Balanced curly brace spans (handles text before/after JSON and multiple objects)
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '{':
            start = i
            depth = 0
            in_str = False
            escape = False
            for j in range(start, n):
                char = text[j]
                if in_str:
                    if escape:
                        escape = False
                    elif char == '\\':
                        escape = True
                    elif char == '"':
                        in_str = False
                else:
                    if char == '"':
                        in_str = True
                    elif char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            candidates.append(text[start:j + 1].strip())
                            i = j
                            break
        i += 1
    return candidates


class JSONGuard:
    """Pure parser and schema validator for candidate JSON extraction."""

    @staticmethod
    def parse(raw_text: str, schema_cls: Type[T]) -> T:
        """Extract and validate JSON against Pydantic schema."""
        clean_text = (raw_text or "").strip()
        if not clean_text:
            raise ValueError("Empty or whitespace-only text cannot be parsed as JSON.")

        # 1. Try direct parsing first
        try:
            data = json.loads(clean_text)
            return schema_cls.model_validate(data)
        except Exception:
            pass

        # 2. Try candidate extraction (fenced blocks and balanced brace objects)
        candidates = extract_json_candidates(clean_text)
        last_error = None
        for cand in candidates:
            try:
                data = json.loads(cand)
                return schema_cls.model_validate(data)
            except Exception as e:
                last_error = e

        err_msg = f"Failed to extract valid JSON matching {schema_cls.__name__}"
        logger.warning("JSONGuard: %s. Last error: %s", err_msg, type(last_error).__name__ if last_error else "None")
        raise ValueError(err_msg) from last_error

    @classmethod
    def parse_with_fallback(cls, raw_text: str, schema_cls: Type[T]) -> T:
        """Compatibility alias for parse()."""
        return cls.parse(raw_text, schema_cls)

