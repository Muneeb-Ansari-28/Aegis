"""Parse-and-Retry Guard for Strict JSON Extraction."""
import json
import logging
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

class JSONGuard:
    @staticmethod
    def parse_with_fallback(raw_text: str, schema_cls: Type[T], max_retries: int = 3) -> T:
        """Extract and validate JSON against Pydantic schema."""
        # Attempt extraction from code fences if present
        clean_text = raw_text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(clean_text)
        return schema_cls.model_validate(data)
