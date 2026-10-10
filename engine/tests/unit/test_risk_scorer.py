from app.agents.risk_scorer import RiskScorer

def test_system_prompt_leakage_severity():
    assert RiskScorer.compute_severity("LLM07", 1.0) == "HIGH"

