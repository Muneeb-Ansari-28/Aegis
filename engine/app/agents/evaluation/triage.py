"""Stage 1 Triage with Llama-Guard-3-1B."""
class TriageFilter:
    """Filters safe vs unsafe responses."""
    async def check_safety(self, prompt: str, response: str) -> bool:
        # Stub for Llama-Guard inference
        return True
