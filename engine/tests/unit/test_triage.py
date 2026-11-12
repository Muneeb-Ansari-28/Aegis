"""Unit test verifying that incomplete TriageFilter scaffold fails closed (Task 10)."""
import pytest
from app.agents.evaluation.triage import TriageFilter


@pytest.mark.asyncio
async def test_triage_filter_raises_not_implemented():
    """Verify that calling incomplete TriageFilter fails closed with NotImplementedError."""
    triage = TriageFilter()
    with pytest.raises(NotImplementedError, match="under development"):
        await triage.check_safety("prompt", "response")

