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


def test_json_guard_extraction_with_surrounding_prose():
    raw = 'Here is the verdict you requested:\n{"name": "prose_test", "score": 95}\nHope this helps!'
    parsed = JSONGuard.parse_with_fallback(raw, SampleModel)
    assert parsed.name == "prose_test"
    assert parsed.score == 95


def test_json_guard_handles_unrelated_surrounding_braces():
    raw = 'Config {mode: debug, v: 1} Result: {"name": "clean", "score": 88} Extra {flag: false}'
    parsed = JSONGuard.parse(raw, SampleModel)
    assert parsed.name == "clean"
    assert parsed.score == 88


def test_json_guard_plain_json():
    raw = '{"name": "plain", "score": 70}'
    parsed = JSONGuard.parse(raw, SampleModel)
    assert parsed.name == "plain"
    assert parsed.score == 70


def test_json_guard_empty_raises_value_error():
    with pytest.raises(ValueError, match="Empty or whitespace-only"):
        JSONGuard.parse("", SampleModel)


def test_json_guard_unparseable_raises_value_error():
    with pytest.raises(ValueError, match="Failed to extract valid JSON"):
        JSONGuard.parse("No JSON object present here at all", SampleModel)

