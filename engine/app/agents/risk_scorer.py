"""Pure Python deterministic risk scorer."""
class RiskScorer:
    WEIGHTS = {"LLM07": 7.5}

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
