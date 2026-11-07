"""Scan Cost & Token Budget Estimator.

Extracted from Agentic Security (agentic_security.probe_actor.cost_module).
Provides token consumption estimation and financial assessment cost modeling
across commercial and local LLM backends.
"""
from typing import Any, Dict, List, Optional
from app.schemas.turn_record import TurnRecord

# Pricing in USD per 1,000,000 tokens (verified baseline)
PRICING_PER_1M_TOKENS: Dict[str, Dict[str, float]] = {
    # Anthropic
    "claude-opus": {"input": 5.00, "output": 25.00},
    "claude-sonnet": {"input": 3.00, "output": 15.00},
    "claude-haiku": {"input": 1.00, "output": 5.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Open / Efficient Models
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "mistral-large": {"input": 0.50, "output": 1.50},
    "mixtral-8x7b": {"input": 0.70, "output": 0.70},
    # Local / On-Premise Models (Zero marginal API fee)
    "ollama": {"input": 0.00, "output": 0.00},
    "llama3.2": {"input": 0.00, "output": 0.00},
    "qwen3:4b": {"input": 0.00, "output": 0.00},
    "local": {"input": 0.00, "output": 0.00},
}

DEFAULT_MODEL = "gpt-4o"


class CostEstimator:
    """Calculates token counts and financial expenditure for automated scans."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Fast token estimation heuristic: ~4 characters per token for English text,
        bounded by word count.
        """
        if not text:
            return 0
        char_based = len(text) / 4.0
        word_based = len(text.split()) * 1.3
        # Use average of character and word estimates for balanced accuracy
        return max(1, int((char_based + word_based) / 2.0))

    @classmethod
    def get_pricing(cls, model_name: str) -> Dict[str, float]:
        """Resolve pricing dictionary for a given model identifier."""
        name_lower = model_name.lower()
        for key, rates in PRICING_PER_1M_TOKENS.items():
            if key in name_lower:
                return rates
        return PRICING_PER_1M_TOKENS[DEFAULT_MODEL]

    @classmethod
    def calculate_turn_cost(
        cls,
        prompt: str,
        response: str,
        model: str = DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        """Calculate token usage and USD cost for a single turn."""
        rates = cls.get_pricing(model)
        p_tokens = cls.estimate_tokens(prompt)
        r_tokens = cls.estimate_tokens(response)
        total_tokens = p_tokens + r_tokens

        cost_usd = (p_tokens * rates["input"] / 1_000_000.0) + (
            r_tokens * rates["output"] / 1_000_000.0
        )

        return {
            "model": model,
            "prompt_tokens": p_tokens,
            "response_tokens": r_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(cost_usd, 6),
        }

    @classmethod
    def calculate_scan_cost(
        cls,
        turns: List[TurnRecord],
        model: str = DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        """Aggregate token usage and estimated cost across all completed scan turns."""
        rates = cls.get_pricing(model)
        total_prompt_tokens = 0
        total_response_tokens = 0

        for turn in turns:
            total_prompt_tokens += cls.estimate_tokens(turn.prompt)
            total_response_tokens += cls.estimate_tokens(turn.response)

        total_tokens = total_prompt_tokens + total_response_tokens
        total_cost_usd = (total_prompt_tokens * rates["input"] / 1_000_000.0) + (
            total_response_tokens * rates["output"] / 1_000_000.0
        )

        return {
            "model": model,
            "total_turns": len(turns),
            "prompt_tokens": total_prompt_tokens,
            "response_tokens": total_response_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(total_cost_usd, 6),
        }

