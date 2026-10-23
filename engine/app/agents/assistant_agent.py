"""Aegis RAG Assistant Agent: local-first security copilot over verified KB."""
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.config import get_settings
from app.llm.ollama_client import OllamaClient
from app.rag.embedder import NomicEmbedder
from app.rag.retriever import AssistantRetriever
from app.rag.vector_store import VectorStore
from app.schemas.assistant import ChatMessage, CitationItem

logger = logging.getLogger(__name__)

SIMPLIFY_RE = re.compile(
    r"(simplify|simpler|simply|simple terms|plain (english|language)|eli5|"
    r"don'?t (understand|get)|like i'?m (5|five)|beginner|layman|too (technical|complex)|"
    r"break (it|this) down|dumb(ed)? (it )?down|make it easier|easier to understand|"
    r"explain (it|that|this|again)? ?(again|better|simply|more simply)?)",
    re.I,
)

FOLLOW_UP_RE = re.compile(
    r"\b(it|its|that|this|the second|the third|next|previous|why|how to fix|how do i fix|give me an example|examples?)\b",
    re.I,
)

NO_DOCS_REPLY = (
    "I don't have enough documentation on that topic in the Aegis knowledge base. "
    "I can answer questions about the OWASP Top 10 for LLM Applications (2026), "
    "Aegis scan operation and calibration, findings evaluation, and remediation playbooks."
)

OWASP_NAME_MAP = {
    "LLM01": "LLM01:2026 Prompt Injection",
    "LLM02": "LLM02:2026 Sensitive Information Disclosure",
    "LLM03": "LLM03:2026 Excessive Agency",
    "LLM04": "LLM04:2026 Supply Chain",
    "LLM05": "LLM05:2026 Data and Model Poisoning",
    "LLM06": "LLM06:2026 Unbounded Consumption",
    "LLM07": "LLM07:2026 Misinformation",
    "LLM08": "LLM08:2026 Hidden Context Exposure",
    "LLM09": "LLM09:2026 Vector and Embedding Weaknesses",
    "LLM10": "LLM10:2026 Improper Output Handling",
}

LEGACY_RENAME_MAP = {
    "system prompt leakage": "LLM08:2026 Hidden Context Exposure (formerly LLM07:2025 System Prompt Leakage)",
    "llm07:2025": "LLM08:2026 Hidden Context Exposure",
    "llm06:2025": "LLM03:2026 Excessive Agency",
    "llm03:2025": "LLM04:2026 Supply Chain",
    "llm04:2025": "LLM05:2026 Data and Model Poisoning",
    "llm05:2025": "LLM10:2026 Improper Output Handling",
    "llm08:2025": "LLM09:2026 Vector and Embedding Weaknesses",
    "llm09:2025": "LLM07:2026 Misinformation",
    "llm10:2025": "LLM06:2026 Unbounded Consumption",
}

CONCEPT_MAP = {
    "excessive agency": "LLM03:2026 Excessive Agency",
    "system prompt leakage": "LLM08:2026 Hidden Context Exposure",
    "improper output handling": "LLM10:2026 Improper Output Handling",
    "prompt injection": "LLM01:2026 Prompt Injection",
    "sensitive information disclosure": "LLM02:2026 Sensitive Information Disclosure",
    "supply chain": "LLM04:2026 Supply Chain",
    "model poisoning": "LLM05:2026 Data and Model Poisoning",
    "unbounded consumption": "LLM06:2026 Unbounded Consumption",
    "misinformation": "LLM07:2026 Misinformation",
    "hidden context exposure": "LLM08:2026 Hidden Context Exposure",
    "vector and embedding weaknesses": "LLM09:2026 Vector and Embedding Weaknesses",
}


def _load_prompt_file(filename: str) -> str:
    """Load a prompt Markdown file from engine/app/agents/prompts/."""
    prompt_path = Path(__file__).resolve().parent / "prompts" / filename
    if not prompt_path.exists():
        logger.warning(f"Prompt file not found: {prompt_path}")
        return ""
    return prompt_path.read_text(encoding="utf-8").strip()


class AssistantAgent:
    """AI Assistant Copilot providing source-grounded answers over Aegis and OWASP KB."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[NomicEmbedder] = None,
        client: Optional[OllamaClient] = None,
    ) -> None:
        """Initialize the assistant agent with storage, embedding, and LLM clients."""
        self.settings = get_settings()
        self.store = vector_store or VectorStore()
        self.embedder = embedder or NomicEmbedder()
        self.client = client or OllamaClient()
        self.retriever = AssistantRetriever(vector_store=self.store, embedder=self.embedder)

        # Load prompts per Rule 2.6
        self.system_prompt = _load_prompt_file("assistant_system.md")
        self.ask_template = _load_prompt_file("assistant_ask.md")
        self.simplify_template = _load_prompt_file("assistant_simplify.md")
        self.rewrite_template = _load_prompt_file("assistant_rewrite.md")

    def detect_intent(self, message: str, mode: Optional[str] = None) -> str:
        """
        Determine whether user intent is standard question answering or simplification.

        Args:
            message: User query text.
            mode: Explicit request mode ("ask" or "simplify").

        Returns:
            "simplify" or "ask".
        """
        if mode == "simplify" or SIMPLIFY_RE.search(message):
            return "simplify"
        return "ask"

    def detect_double_simplify(
        self,
        message: str,
        history: List[Union[ChatMessage, Dict[str, Any]]],
    ) -> bool:
        """
        Detect if the user is asking for a second, even simpler explanation.

        Args:
            message: Current user message.
            history: List of previous conversation turns.

        Returns:
            True if user requests double simplification, False otherwise.
        """
        if "even simpler" in message.lower() or "simpler please" in message.lower():
            return True
        user_turns = [
            m.text if isinstance(m, ChatMessage) else m.get("text", "")
            for m in history
            if (m.role if isinstance(m, ChatMessage) else m.get("role")) == "user"
        ]
        return len(user_turns) >= 1 and bool(SIMPLIFY_RE.search(user_turns[-1]))

    def normalize_query(self, query: str) -> str:
        """
        Expand bare vulnerability IDs and legacy terminology for accurate retrieval.

        Args:
            query: Raw user query string.

        Returns:
            Expanded search query string.
        """
        norm = query
        q_lower = query.lower()

        # Handle concept names (e.g. excessive agency -> LLM03:2026)
        for concept_phrase, target_term in CONCEPT_MAP.items():
            if concept_phrase in q_lower and target_term not in norm:
                norm += f" {target_term}"

        # Handle legacy 2025 mappings
        for legacy_term, target_term in LEGACY_RENAME_MAP.items():
            if legacy_term in q_lower and target_term not in norm:
                norm += f" {target_term}"

        # Expand bare LLMxx references if not already expanded
        for code, full_name in OWASP_NAME_MAP.items():
            pattern = re.compile(rf"\b{code}\b(?!:2026)", re.I)
            if pattern.search(query) and full_name not in norm:
                norm += f" {full_name}"

        return norm

    async def standalone_query(
        self,
        message: str,
        history: List[Union[ChatMessage, Dict[str, Any]]],
    ) -> str:
        """
        Rewrite conversational follow-ups into a self-contained search query.

        Args:
            message: Current user question.
            history: List of previous turns.

        Returns:
            Rewritten standalone search query.
        """
        if not history or not FOLLOW_UP_RE.search(message):
            return self.normalize_query(message)

        recent = history[-4:]
        turns: List[str] = []
        for turn in recent:
            role = turn.role if isinstance(turn, ChatMessage) else turn.get("role", "")
            text = turn.text if isinstance(turn, ChatMessage) else turn.get("text", "")
            turns.append(f"{role}: {text}")

        history_block = "\n".join(turns)
        prompt = self.rewrite_template.format(history_turns=history_block, message=message)

        try:
            rewritten = await self.client.generate(
                model=self.settings.MODEL_ASSISTANT,
                prompt=prompt,
                temperature=0.1,
            )
            cleaned = rewritten.strip().replace('"', "")
            if cleaned and len(cleaned) < 250:
                return self.normalize_query(cleaned)
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}. Falling back to normalized query.")

        return self.normalize_query(message)

    async def chat(
        self,
        message: str,
        history: Optional[List[Union[ChatMessage, Dict[str, Any]]]] = None,
        mode: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main chat handler processing user queries, retrieving context, and generating answers.

        Args:
            message: User input message.
            history: List of previous turns.
            mode: Explicit request mode ("ask" or "simplify").
            reply_to_message_id: Optional reference for specific message simplification.

        Returns:
            Dict containing 'reply', 'source_ids', 'citations', and 'mode'.
        """
        hist = history or []
        intent = self.detect_intent(message, mode)

        # ----------------------------------------------------
        # Simplify Mode
        # ----------------------------------------------------
        if intent == "simplify":
            prev_assistant = None
            for turn in reversed(hist):
                role = turn.role if isinstance(turn, ChatMessage) else turn.get("role")
                if role == "assistant":
                    prev_assistant = turn
                    break

            if prev_assistant:
                prev_text = prev_assistant.text if isinstance(prev_assistant, ChatMessage) else prev_assistant.get("text", "")
                prev_ids = prev_assistant.source_ids if isinstance(prev_assistant, ChatMessage) else prev_assistant.get("source_ids", [])

                chunks = self.store.get_by_ids(prev_ids)
                doc_list = chunks.get("documents", [])
                meta_list = chunks.get("metadatas", [])
                id_list = chunks.get("ids", [])

                # Extract risk IDs and retrieve simple companion chunks
                risk_ids = {m.get("risk_id") for m in meta_list if m.get("risk_id")}
                simple_chunks = self.store.get_simple(risk_ids)
                s_docs = simple_chunks.get("documents", [])
                s_metas = simple_chunks.get("metadatas", [])
                s_ids = simple_chunks.get("ids", [])

                merged_docs = doc_list + s_docs
                merged_metas = meta_list + s_metas
                merged_ids = id_list + s_ids

                formatted_ctx = AssistantRetriever.format_context(merged_docs, merged_metas)
                is_double = self.detect_double_simplify(message, hist)
                extra = "Even simpler: maximum 3 sentences with one everyday analogy." if is_double else ""

                prompt = self.simplify_template.format(
                    context=formatted_ctx,
                    previous_answer=prev_text,
                    extra_instruction=extra,
                )

                try:
                    reply = await self.client.generate(
                        model=self.settings.MODEL_ASSISTANT,
                        system=self.system_prompt,
                        prompt=prompt,
                        temperature=0.2,
                    )
                except Exception as e:
                    logger.error(f"Generation error in simplify mode: {e}")
                    reply = "I encountered an error generating the simplified explanation. Please ensure Ollama is running."

                citations = [
                    CitationItem(
                        source=m.get("source", "aegis"),
                        source_title=m.get("source_title", ""),
                        risk_id=m.get("risk_id", ""),
                        section=m.get("section", ""),
                        page=m.get("page"),
                    ).model_dump()
                    for m in merged_metas
                ]

                return {
                    "reply": reply,
                    "source_ids": merged_ids,
                    "citations": citations,
                    "mode": "simplify",
                }
            else:
                return {
                    "reply": "What previous explanation or security topic would you like me to explain more simply?",
                    "source_ids": [],
                    "citations": [],
                    "mode": "simplify",
                }

        # ----------------------------------------------------
        # Standard Ask Mode
        # ----------------------------------------------------
        search_query = await self.standalone_query(message, hist)
        docs, metas, ids = await self.retriever.retrieve(
            query=search_query,
            n_results=self.settings.RAG_TOP_K,
            relevance_cutoff=self.settings.RAG_RELEVANCE_CUTOFF,
        )

        if not docs:
            return {
                "reply": NO_DOCS_REPLY,
                "source_ids": [],
                "citations": [],
                "mode": "ask",
            }

        formatted_ctx = AssistantRetriever.format_context(docs, metas)
        prompt = self.ask_template.format(context=formatted_ctx, question=message)

        try:
            reply = await self.client.generate(
                model=self.settings.MODEL_ASSISTANT,
                system=self.system_prompt,
                prompt=prompt,
                temperature=0.2,
            )
        except Exception as e:
            logger.error(f"Generation error in ask mode: {e}")
            reply = "I encountered an error generating the response. Please ensure the local Ollama service is running."

        citations = [
            CitationItem(
                source=m.get("source", "aegis"),
                source_title=m.get("source_title", ""),
                risk_id=m.get("risk_id", ""),
                section=m.get("section", ""),
                page=m.get("page"),
            ).model_dump()
            for m in metas
        ]

        return {
            "reply": reply,
            "source_ids": ids,
            "citations": citations,
            "mode": "ask",
        }
