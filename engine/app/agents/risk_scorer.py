"""Pure Python deterministic risk scorer."""
class RiskScorer:
    WEIGHTS = {
        "LLM01": 9.0,
        "LLM02": 8.0,
        "LLM03": 8.5,
        "LLM04": 7.0,
        "LLM05": 7.5,
        "LLM06": 6.5,
        "LLM07": 6.0,
        "LLM08": 7.5,
        "LLM09": 6.5,
        "LLM10": 7.0,
    }

    @classmethod
    def compute_severity(cls, category: str, confidence: float) -> str:
        score = cls.WEIGHTS.get(category, 5.0) * confidence
        if score >= 8.0: return "CRITICAL"
        if score >= 6.0: return "HIGH"
        if score >= 4.0: return "MEDIUM"
        return "LOW"

    @classmethod
    def compute_grade(cls, penalties: float) -> float:
        return max(0.0, min(100.0, 100.0 - penalties))
