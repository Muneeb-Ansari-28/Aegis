"""LLM-Powered Fuzzy Site-Type Classifier for Reconnaissance."""
import logging
from typing import Optional
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.llm.json_guard import JSONGuard
from app.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Aegis Reconnaissance Agent.
Analyze the provided web page title, body text snippet, and chatbot self-introduction.
Classify the target application and output strictly valid JSON matching this schema:
{
  "site_type": "customer_support" | "code_assistant" | "internal_knowledge_base" | "creative_bot" | "general_assistant" | "ecommerce_bot",
  "primary_domain": "string (e.g. software, finance, healthcare, retail, corporate, general)",
  "confidence": float (0.0 to 1.0),
  "reasoning": "brief explanation"
}
Do not include markdown fences or any other text outside the JSON object.
"""


class ClassifierOutput(BaseModel):
    site_type: str = Field(
        default="general_assistant",
        description="Classified site type role",
    )
    primary_domain: str = Field(
        default="general",
        description="Target subject domain",
    )
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Classification confidence",
    )
    reasoning: str = Field(
        default="",
        description="Classification rationale",
    )


class SiteTypeClassifier:
    """
    Executes a single fuzzy classification step via Ollama (Qwen3-4B Q4 / Llama 3.2).
    Includes deterministic fallback if LLM is unreachable.
    """

    def __init__(self, model_name: Optional[str] = None):
        settings = get_settings()
        self.model_name = model_name or settings.MODEL_RECON
        self.ollama = OllamaClient()

    async def classify(
        self,
        page_title: str = "",
        page_text: str = "",
        scope_reply: str = "",
    ) -> ClassifierOutput:
        """
        Classify target application based on surface text and probe responses.
        """
        user_prompt = (
            f"Target Page Title: {page_title}\n\n"
            f"Page Text Excerpt:\n{page_text[:1200]}\n\n"
            f"Chatbot Self-Described Scope:\n{scope_reply[:600]}\n\n"
            "Classify the site type and primary domain according to the schema."
        )

        try:
            if not await self.ollama.is_available():
                return self._deterministic_fallback(page_title, page_text, scope_reply)

            raw_response = await self.ollama.generate(
                model=self.model_name,
                prompt=user_prompt,
                system=SYSTEM_PROMPT,
            )
            parsed = JSONGuard.parse_with_fallback(raw_response, ClassifierOutput)
            logger.info(
                f"Recon classification: type={parsed.site_type}, domain={parsed.primary_domain}, conf={parsed.confidence}"
            )
            return parsed
        except Exception as e:
            logger.warning(
                f"LLM site classification failed ({e}). Using deterministic fallback."
            )
            return self._deterministic_fallback(page_title, page_text, scope_reply)

    def _deterministic_fallback(
        self,
        page_title: str,
        page_text: str,
        scope_reply: str,
    ) -> ClassifierOutput:
        """Deterministic keyword-based classification fallback."""
        combined = f"{page_title} {page_text} {scope_reply}".lower()

        if any(w in combined for w in ["support", "help desk", "faq", "customer service", "agent"]):
            return ClassifierOutput(
                site_type="customer_support",
                primary_domain="support",
                confidence=0.75,
                reasoning="Heuristic fallback matched customer support keywords.",
            )
        if any(w in combined for w in ["code", "developer", "git", "api", "programming", "python", "software"]):
            return ClassifierOutput(
                site_type="code_assistant",
                primary_domain="software",
                confidence=0.75,
                reasoning="Heuristic fallback matched software/code keywords.",
            )
        if any(w in combined for w in ["internal", "knowledge base", "wiki", "docs", "documentation", "handbook"]):
            return ClassifierOutput(
                site_type="internal_knowledge_base",
                primary_domain="corporate",
                confidence=0.75,
                reasoning="Heuristic fallback matched internal knowledge base keywords.",
            )
        if any(w in combined for w in ["shop", "store", "product", "cart", "order", "price"]):
            return ClassifierOutput(
                site_type="ecommerce_bot",
                primary_domain="retail",
                confidence=0.70,
                reasoning="Heuristic fallback matched ecommerce keywords.",
            )

        return ClassifierOutput(
            site_type="general_assistant",
            primary_domain="general",
            confidence=0.60,
            reasoning="Default heuristic fallback for general chatbot.",
        )
