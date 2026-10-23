"""FastAPI Endpoints for Aegis AI Assistant."""
import logging
from fastapi import APIRouter, HTTPException, status
from app.agents.assistant_agent import AssistantAgent
from app.core.config import get_settings
from app.llm.ollama_client import OllamaClient
from app.rag.vector_store import VectorStore
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
_assistant_agent: AssistantAgent | None = None


def get_assistant_agent() -> AssistantAgent:
    """Lazy singleton provider for the AssistantAgent."""
    global _assistant_agent
    if _assistant_agent is None:
        _assistant_agent = AssistantAgent()
    return _assistant_agent


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="Chat with Aegis AI Assistant",
    description="Ask security questions grounded in OWASP Top 10 2026 and Aegis documentation.",
)
async def chat_with_assistant(req: AssistantChatRequest) -> AssistantChatResponse:
    """
    Handle user chat message, retrieve relevant KB context, and return grounded answer.

    Args:
        req: AssistantChatRequest with message, history, and optional mode.

    Returns:
        AssistantChatResponse with answer reply, source chunk IDs, citations, and mode.
    """
    cleaned_message = req.message.strip()
    if not cleaned_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    agent = get_assistant_agent()
    try:
        result = await agent.chat(
            message=cleaned_message,
            history=req.history,
            mode=req.mode,
            reply_to_message_id=req.reply_to_message_id,
        )
        return AssistantChatResponse(**result)
    except Exception as e:
        logger.error(f"Error handling assistant chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the assistant request.",
        )


@router.get(
    "/status",
    response_model=AssistantStatusResponse,
    summary="Get Assistant subsystem status",
    description="Returns Ollama connectivity, indexed chunk count, and model configuration.",
)
async def get_assistant_status() -> AssistantStatusResponse:
    """
    Check the operational status of the RAG assistant and Ollama daemon.

    Returns:
        AssistantStatusResponse with health details.
    """
    settings = get_settings()
    client = OllamaClient()
    store = VectorStore()

    ollama_ok = await client.is_available()
    chunk_count = store.count()

    overall_status = "ready" if (ollama_ok and chunk_count > 0) else "degraded"

    return AssistantStatusResponse(
        status=overall_status,
        ollama_available=ollama_ok,
        kb_chunks_indexed=chunk_count,
        embed_model=settings.MODEL_EMBED,
        assistant_model=settings.MODEL_ASSISTANT,
    )
