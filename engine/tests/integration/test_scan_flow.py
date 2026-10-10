import pytest
from app.agents.orchestrator import Orchestrator
from app.adapters.playwright_web import PlaywrightWebAdapter

@pytest.mark.asyncio
async def test_orchestrator_skeleton():
    adapter = PlaywrightWebAdapter(target_url="http://localhost:8000")
    orchestrator = Orchestrator(scan_id="test-scan", adapter=adapter, max_budget=2)
    verdict = await orchestrator.run()
    assert orchestrator.state.value == "COMPLETED"
