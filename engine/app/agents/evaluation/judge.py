"""Stage 2 rubric judge for LLM07 system-prompt disclosure."""
from app.schemas.verdict import JudgeVerdict

class RubricJudge:
    """Stub for Qwen judge using the LLM07 rubric."""
    async def judge(self, prompt: str, response: str) -> JudgeVerdict:
        return JudgeVerdict(
            exploited=False,
            confidence=0.85,
            rationale="No planted canary or distinctive system-prompt content was confirmed in this response.",
            category="LLM07",
        )
