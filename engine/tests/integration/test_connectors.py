import pytest
from app.adapters.playwright_web import PlaywrightWebAdapter

@pytest.mark.asyncio
async def test_playwright_mock():
    adapter = PlaywrightWebAdapter(target_url="http://localhost:8000")
    record = await adapter.send_prompt("Test prompt", 1)
    assert record.prompt == "Test prompt"
    assert record.turn_index == 1
