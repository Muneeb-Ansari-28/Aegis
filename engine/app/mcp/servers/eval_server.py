"""MCP Server: aegis-eval. Exposes deterministic canary and overlap checks."""
from app.agents.evaluation.deterministic import DeterministicDetector

def canary_check(text: str, canary: str = "AEGIS-CANARY-7731") -> bool:
    return DeterministicDetector(canary=canary).canary_check(text)

def overlap_score(text: str, known_prompt: str) -> float:
    return DeterministicDetector(known_prompt=known_prompt).overlap_score(text)
