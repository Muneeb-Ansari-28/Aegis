import json
from pathlib import Path
from app.agents.evaluation.deterministic import DeterministicDetector

def test_benchmark_pairs():
    benchmark_file = Path(__file__).parent / "benchmark_pairs.json"
    with open(benchmark_file, "r", encoding="utf-8-sig") as f:
        pairs = json.load(f)
    detector = DeterministicDetector()
    for pair in pairs:
        detected = detector.canary_check(pair["response"])
        assert detected is pair["ground_truth_exploited"]
