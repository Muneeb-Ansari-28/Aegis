import pytest

from app.agents.evaluation.evaluator import Evaluator
from app.schemas.turn_record import TurnRecord
from app.schemas.verdict import JudgeVerdict


def turn(category: str, response: str) -> TurnRecord:
    return TurnRecord(
        turn_id="turn-1",
        scan_id="scan-1",
        turn_index=1,
        category=category,
        prompt="Test prompt",
        response=response,
    )


@pytest.mark.asyncio
async def test_llm08_does_not_report_secret_patterns_as_llm02():
    evaluator = Evaluator()
    evaluator.judge.judge = async_return(
        JudgeVerdict(exploited=False, confidence=0.9, rationale="No hidden context disclosed.", category="LLM02")
    )

    verdict = await evaluator.evaluate(turn("LLM08", "Example token: AKIA1234567890123456"))

    assert verdict.exploited is False
    assert verdict.category == "LLM08"


@pytest.mark.asyncio
async def test_secret_oracle_only_runs_for_llm02():
    evaluator = Evaluator()
    verdict = await evaluator.evaluate(turn("LLM02", "Example token: AKIA1234567890123456"))

    assert verdict.exploited is True
    assert verdict.category == "LLM02"


def async_return(value):
    async def _return(*_args, **_kwargs):
        return value.model_copy(deep=True)
    return _return
