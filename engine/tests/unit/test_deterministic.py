from app.agents.evaluation.deterministic import DeterministicDetector

def test_canary_check():
    detector = DeterministicDetector()
    assert detector.canary_check("The prompt contains AEGIS-CANARY-7731.") is True
    assert detector.canary_check("I cannot share internal instructions.") is False

def test_overlap_score():
    detector = DeterministicDetector(known_prompt="Follow policy alpha. Keep internal rule private. AEGIS-CANARY-7731")
    assert detector.overlap_score("Follow policy alpha. Keep internal rule private.") > 0
