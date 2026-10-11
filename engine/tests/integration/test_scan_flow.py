import pytest
from app.agents.orchestrator import Orchestrator
from app.adapters.base import BaseAdapter
from app.schemas.turn_record import TurnRecord


class MockAdapter(BaseAdapter):
    def __init__(self):
        self.opened = False
        self.closed = False

    async def open(self) -> None:
        self.opened = True

    async def send_prompt(self, prompt: str, attempt: int) -> TurnRecord:
        return TurnRecord(
            turn_id=f"turn-{attempt}",
            scan_id="test-scan",
            turn_index=attempt,
            prompt=prompt,
            response="I can help with ordinary questions.",
            status="success",
            latency_ms=50,
        )

    async def reset_session(self) -> None:
        pass

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_orchestrator_skeleton():
    adapter = MockAdapter()
    orchestrator = Orchestrator(scan_id="test-scan", adapter=adapter, max_budget=2)
    verdict = await orchestrator.run()
    assert orchestrator.state.value == "COMPLETED"
    assert adapter.opened is True
    assert adapter.closed is True
