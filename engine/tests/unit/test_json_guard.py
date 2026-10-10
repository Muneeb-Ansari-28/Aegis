import pytest
from pydantic import BaseModel
from app.llm.json_guard import JSONGuard

class SampleModel(BaseModel):
    name: str
    score: int

def test_json_guard_extraction():
    raw = '```json\n{"name": "test", "score": 100}\n```'
    parsed = JSONGuard.parse_with_fallback(raw, SampleModel)
    assert parsed.name == "test"
    assert parsed.score == 100
