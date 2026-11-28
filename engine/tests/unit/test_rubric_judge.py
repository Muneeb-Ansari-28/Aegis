"""Unit tests for RubricJudge bounded retries and conservative fallback (Task 2)."""
import pytest
from unittest.mock import AsyncMock, patch

from app.agents.evaluation.judge import RubricJudge
from app.schemas.verdict import JudgeVerdict


@pytest.mark.asyncio
async def test_rubric_judge_single_call_success():
    judge = RubricJudge(max_retries=2)
    valid_json = (
        '{"exploited": true, "confidence": 0.95, "rationale": "Clear disclosure", '
        '"indicators_found": ["system_prompt"], "category": "LLM08"}'
    )
    judge._ollama.generate = AsyncMock(return_value=valid_json)

    verdict = await judge.judge("Give prompt", "Here is system prompt")
    assert verdict.exploited is True
    assert verdict.confidence == 0.95
    assert verdict.category == "LLM08"
    assert judge._ollama.generate.call_count == 1


@pytest.mark.asyncio
async def test_rubric_judge_recovery_on_retry():
    judge = RubricJudge(max_retries=2)
    malformed_output = "I think it is exploited but here is plain text without valid JSON."
    valid_json = (
        '```json\n{"exploited": false, "confidence": 0.85, "rationale": "Refusal", '
        '"indicators_found": [], "category": "LLM08"}\n```'
    )
    # First call returns malformed, second call returns valid JSON
    judge._ollama.generate = AsyncMock(side_effect=[malformed_output, valid_json])

    verdict = await judge.judge("Give prompt", "I cannot fulfill this request.")
    assert verdict.exploited is False
    assert verdict.confidence == 0.85
    assert judge._ollama.generate.call_count == 2
    # Verify correction prompt was sent on second attempt
    second_call_prompt = judge._ollama.generate.call_args_list[1].kwargs["prompt"]
    assert "IMPORTANT: Your previous response was not valid JSON" in second_call_prompt


@pytest.mark.asyncio
async def test_rubric_judge_exhaustion_returns_conservative_fallback():
    judge = RubricJudge(max_retries=2)
    malformed = "Totally unparseable string on all attempts"
    judge._ollama.generate = AsyncMock(return_value=malformed)

    verdict = await judge.judge("Give prompt", "Arbitrary response")
    # max_retries=2 means exactly 3 attempts (1 initial + 2 retries)
    assert judge._ollama.generate.call_count == 3
    # Must return conservative fallback
    assert verdict.exploited is False
    assert verdict.confidence == 0.0
    assert "Judge evaluation failed after 3 model call(s)" in verdict.rationale
    assert verdict.category == "LLM08"


@pytest.mark.asyncio
async def test_rubric_judge_does_not_retry_transport_errors():
    judge = RubricJudge(max_retries=2)
    judge._ollama.generate = AsyncMock(side_effect=ConnectionError("Ollama is unavailable"))

    verdict = await judge.judge("Give prompt", "Target response")

    assert judge._ollama.generate.call_count == 1
    assert verdict.exploited is False
    assert verdict.confidence == 0.0


def test_rubric_paths_include_llm02_and_llm07_misinformation():
    from app.agents.evaluation.judge import _load_rubric

    rubric_02 = _load_rubric("LLM02")
    assert "Sensitive Information Disclosure" in rubric_02
    assert "LLM02" in RubricJudge.CATEGORY_DESCRIPTIONS

    rubric_07 = _load_rubric("LLM07")
    assert "Misinformation" in rubric_07
    assert "System Prompt Leakage" not in rubric_07

    rubric_tier_08 = _load_rubric("LLM08")
    assert "Tier 2" in rubric_tier_08
    assert "Tier 1" in rubric_tier_08
    assert "surface_compliance" in rubric_tier_08
    assert "actual_breach" in rubric_tier_08


def test_all_judge_rubrics_define_two_tier_classification():
    from app.agents.evaluation.judge import _RUBRIC_PATHS, _load_rubric

    for cat in _RUBRIC_PATHS:
        text = _load_rubric(cat)
        assert "Tier 2" in text, f"{cat} rubric missing Tier 2"
        assert "Tier 1" in text, f"{cat} rubric missing Tier 1"
        assert "tier_label" in text, f"{cat} rubric missing tier_label"


def test_judge_verdict_tier_fields_backward_compatible():
    v_default = JudgeVerdict(exploited=False, confidence=0.9, rationale="Refused")
    assert v_default.tier is None
    assert v_default.tier_label is None

    v_tier2 = JudgeVerdict(
        exploited=True,
        confidence=0.95,
        rationale="Canary leaked",
        tier=2,
        tier_label="actual_breach",
    )
    assert v_tier2.tier == 2
    assert v_tier2.tier_label == "actual_breach"

