"""Stage 1 Triage with Llama-Guard-3-1B (Experimental / Unsupported scaffold)."""
import logging

logger = logging.getLogger(__name__)


class TriageFilter:
    """Experimental scaffold for model-based response safety triage.

    Under development: not supported in automated scan pipelines.
    Raises NotImplementedError on invocation to prevent false safety claims.
    """

    async def check_safety(self, prompt: str, response: str) -> bool:
        """Evaluate response safety.

        Raises:
            NotImplementedError: Automated Llama-Guard triage is not implemented.
        """
        raise NotImplementedError(
            "TriageFilter (Llama-Guard-3-1B) is under development and not supported for automated triage. "
            "Do not rely on this filter for safety verdicts."
        )
