"""Unit tests for Stage 1 TriageFilter with Llama-Guard-3-1B."""
from unittest.mock import AsyncMock
import pytest
from app.agents.evaluation.triage import TriageFilter


@pytest.mark.asyncio
async def test_triage_filter_safe_response():
    """Verify that a 'safe' response from Llama-Guard returns True."""
    mock_ollama = AsyncMock()
    mock_ollama.generate.return_value = "safe\n"

    triage = TriageFilter(ollama_client=mock_ollama)
    result = await triage.check_safety("Hello", "Hello! How can I help you?")

    assert result is True
    assert mock_ollama.generate.call_count == 1
    # Verify num_gpu=0 was specified for CPU offload
    kwargs = mock_ollama.generate.call_args.kwargs
    assert kwargs.get("num_gpu") == 0


@pytest.mark.asyncio
async def test_triage_filter_unsafe_response():
    """Verify that an 'unsafe' classification from Llama-Guard returns False."""
    mock_ollama = AsyncMock()
    mock_ollama.generate.return_value = "unsafe\nS1"

    triage = TriageFilter(ollama_client=mock_ollama)
    result = await triage.check_safety("Harmful prompt", "Harmful response content")

    assert result is False


@pytest.mark.asyncio
async def test_triage_filter_error_fallback():
    """Verify that Ollama connection error safely fails open to Stage 2 (returns False)."""
    mock_ollama = AsyncMock()
    mock_ollama.generate.side_effect = ConnectionError("Ollama unreachable")

    triage = TriageFilter(ollama_client=mock_ollama)
    result = await triage.check_safety("Test prompt", "Test response")

    assert result is False


@pytest.mark.asyncio
async def test_triage_filter_empty_inputs():
    """Verify that empty inputs safely return False without invoking the model."""
    mock_ollama = AsyncMock()

    triage = TriageFilter(ollama_client=mock_ollama)
    assert await triage.check_safety("", "Response") is False
    assert await triage.check_safety("Prompt", "") is False
    assert mock_ollama.generate.call_count == 0
