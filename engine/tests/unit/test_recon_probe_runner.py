"""Unit tests for Active Benign Probe Runner."""
import pytest
from app.adapters.base import BaseAdapter
from app.recon.probe_runner import ProbeRunner
from app.schemas.turn_record import TurnRecord


class MockChatAdapter(BaseAdapter):
    def __init__(self, with_memory: bool = True, with_rag: bool = True):
        self.with_memory = with_memory
        self.with_rag = with_rag

    async def open(self):
        pass

    async def close(self):
        pass

    async def reset_session(self):
        pass

    async def send_prompt(self, prompt: str, attempt: int, scan_id: str = "test", strategy: str = None) -> TurnRecord:
        reply = "I am a helpful assistant."
        if strategy == "probe_scope":
            reply = "I provide customer support for our banking portal."
        elif strategy == "probe_rag":
            if self.with_rag:
                reply = "According to our official documentation [1], account limits are $5,000. Source: https://example.com/docs"
            else:
                reply = "I do not have access to external documents."
        elif strategy == "probe_mem_1":
            reply = "I will remember that your favorite color is AegisCyan42."
        elif strategy == "probe_mem_2":
            if self.with_memory:
                reply = "Your reference color is AegisCyan42."
            else:
                reply = "I have no memory of our previous messages."
        elif strategy == "probe_render":
            reply = "Here is the code: <b>BoldTestMarker</b> and `alert(1)`"
        elif strategy == "probe_tools":
            reply = "I cannot trigger any external calculators or tools."

        return TurnRecord(
            turn_id=f"turn-{attempt}",
            scan_id=scan_id,
            turn_index=attempt,
            prompt=prompt,
            response=reply,
            strategy=strategy,
            status="success",
        )


@pytest.mark.asyncio
async def test_probe_runner_detects_rag_and_memory():
    adapter = MockChatAdapter(with_memory=True, with_rag=True)
    runner = ProbeRunner(adapter=adapter, scan_id="test-scan-123")
    result = await runner.run_probes(persist_turns=False)

    assert len(result.turns) == 6
    # All turns MUST have category = RECON
    for turn in result.turns:
        assert turn.category == "RECON"

    # Capability detections
    assert result.analysis.rag_detected is True
    assert result.analysis.rag_confidence >= 0.70
    assert result.analysis.memory_detected is True
    assert result.analysis.memory_confidence >= 0.90
    assert result.analysis.html_rendered is True
    assert "banking portal" in result.analysis.scope_summary.lower()


@pytest.mark.asyncio
async def test_probe_runner_detects_stateless_no_rag():
    adapter = MockChatAdapter(with_memory=False, with_rag=False)
    runner = ProbeRunner(adapter=adapter, scan_id="test-scan-456")
    result = await runner.run_probes(persist_turns=False)

    assert result.analysis.memory_detected is False
    assert result.analysis.rag_detected is False

