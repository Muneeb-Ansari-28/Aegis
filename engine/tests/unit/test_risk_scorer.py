from app.agents.risk_scorer import RiskScorer

def test_hidden_context_exposure_severity():
    assert RiskScorer.compute_severity("LLM08", 1.0) == "HIGH"

