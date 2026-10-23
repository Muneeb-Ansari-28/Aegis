"""Pydantic Schemas for Aegis AI Assistant."""
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    """Structured citation metadata pointing to a verified source chunk."""

    source: str = Field(..., description="Source identifier, e.g. owasp_llm_top10_2026 or aegis")
    source_title: str = Field(default="", description="Human-readable title of source document")
    risk_id: str = Field(default="", description="OWASP Risk ID (e.g. LLM08:2026) or empty")
    section: str = Field(default="", description="Section or subsection title")
    page: Optional[Union[int, str]] = Field(default=None, description="Printed source page number")


class ChatMessage(BaseModel):
    """Single chat turn in conversation history."""

    role: str = Field(..., description="Role of the sender ('user' or 'assistant')")
    text: str = Field(..., description="Text content of the message")
    source_ids: List[str] = Field(default_factory=list, description="IDs of chunks supporting this answer")
    citations: List[CitationItem] = Field(default_factory=list, description="Structured citation metadata")


class AssistantChatRequest(BaseModel):
    """Payload for conversational assistant queries."""

    message: str = Field(..., description="User question or input prompt")
    history: List[ChatMessage] = Field(default_factory=list, description="Prior conversation turns for context")
    mode: Optional[str] = Field(default=None, description="Optional explicit mode ('ask' or 'simplify')")
    reply_to_message_id: Optional[str] = Field(default=None, description="ID or reference to message being simplified")


class AssistantChatResponse(BaseModel):
    """Structured response returned by the Aegis AI Assistant."""

    reply: str = Field(..., description="Assistant answer text")
    source_ids: List[str] = Field(default_factory=list, description="Chunk IDs used as grounded context")
    citations: List[CitationItem] = Field(default_factory=list, description="Structured citation metadata")
    mode: str = Field(default="ask", description="Mode executed ('ask' or 'simplify')")


class AssistantStatusResponse(BaseModel):
    """Health and status details of the RAG assistant subsystem."""

    status: str = Field(..., description="Operational status ('ready' or 'degraded')")
    ollama_available: bool = Field(..., description="Whether Ollama daemon is reachable")
    kb_chunks_indexed: int = Field(..., description="Total knowledge chunks indexed in vector store")
    embed_model: str = Field(..., description="Configured embedding model")
    assistant_model: str = Field(..., description="Configured conversational assistant model")
