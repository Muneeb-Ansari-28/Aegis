"""Deterministic Test Planner Rule Engine (Step 0b).

Converts a TargetProfile into a prioritized, bounded TestPlan
using non-LLM Python logic and the 'Unknown ≠ Absent' safe-fallback policy.
"""
import logging
from typing import List

from app.agents.planner.prompt_filter import PromptMetadataFilter
from app.recon.schemas import TargetProfile
from app.schemas.test_plan import CategoryPlan, TestPlan

logger = logging.getLogger(__name__)

OWASP_NAMES = {
    "LLM01": "Prompt Injection",
    "LLM02": "Sensitive Information Disclosure",
    "LLM03": "Excessive Agency",
    "LLM04": "Data and Model Poisoning",
    "LLM05": "Improper Output Handling",
    "LLM06": "Excessive Agency",
    "LLM07": "System Prompt Leakage",
    "LLM08": "Vector and Embedding Weaknesses",
    "LLM09": "Misinformation",
    "LLM10": "Improper Output Handling",
}


class TestPlanner:
    """
    Translates TargetProfile capabilities into an actionable, bounded TestPlan.
    100% deterministic, non-LLM control plane.
    """

    @classmethod
    def build_test_plan(cls, profile: TargetProfile) -> TestPlan:
        """
        Synthesize prioritized categories and attempt budgets from the TargetProfile.
        """
        categories: List[CategoryPlan] = []

        # Rule 1: LLM08 (Vector and Embedding Weaknesses)
        cat_llm08 = cls._plan_llm08(profile)
        categories.append(cat_llm08)

        # Rule 2: LLM01 (Prompt Injection - Direct & Indirect)
        cat_llm01 = cls._plan_llm01(profile)
        categories.append(cat_llm01)

        # Rule 3: LLM07 (System Prompt Leakage / Direct Disclosure)
        cat_llm07 = cls._plan_llm07(profile)
        categories.append(cat_llm07)

        # Rule 4: LLM03 (Excessive Agency)
        cat_llm03 = cls._plan_llm03(profile)
        categories.append(cat_llm03)

        # Rule 5: LLM10 (Improper Output Handling)
        cat_llm10 = cls._plan_llm10(profile)
        categories.append(cat_llm10)

        # Rule 6: LLM02 (Sensitive Information Disclosure)
        cat_llm02 = cls._plan_llm02(profile)
        categories.append(cat_llm02)

        # Attach applicable prompt IDs to each scheduled category
        for cat_plan in categories:
            if cat_plan.status == "scheduled":
                prompt_ids = PromptMetadataFilter.get_applicable_prompts(
                    category=cat_plan.category,
                    profile=profile,
                )
                cat_plan.applicable_prompt_ids = prompt_ids

        total_budget = sum(c.budget for c in categories if c.status == "scheduled")

        profile_summary = {
            "site_type": profile.site_type.value,
            "has_rag": profile.has_rag.detected,
            "rag_confidence": profile.has_rag.confidence,
            "has_tools": profile.has_tools.detected,
            "memory": profile.has_conversation_memory.detected,
            "streaming": profile.has_streaming.value,
            "frameworks": profile.detected_frameworks,
        }

        return TestPlan(
            target_id=profile.target_id,
            target_profile_summary=profile_summary,
            categories=categories,
            total_budget=total_budget,
        )

    @classmethod
    def _plan_llm08(cls, profile: TargetProfile) -> CategoryPlan:
        """
        RAG Rule:
        - If RAG detected (conf >= 0.6): High priority 1, budget 10.
        - If affirmative proof of NO RAG (conf >= 0.85): Mark Not Applicable.
        - Else (unknown): Safe fallback -> scheduled with priority 7, budget 5.
        """
        if profile.has_rag.detected and profile.has_rag.confidence >= 0.6:
            return CategoryPlan(
                category="LLM08",
                name="Vector and Embedding Weaknesses",
                priority=1,
                budget=10,
                status="scheduled",
                reason=f"RAG architecture detected ({profile.has_rag.source}, conf={profile.has_rag.confidence}): testing retrieval boundaries and context leakage.",
            )
        elif not profile.has_rag.detected and profile.has_rag.confidence >= 0.85:
            return CategoryPlan(
                category="LLM08",
                name="Vector and Embedding Weaknesses",
                priority=10,
                budget=0,
                status="not_applicable",
                reason="Not Applicable (recon: no RAG detected).",
            )
        else:
            # Safe-fallback: unknown is not absent
            return CategoryPlan(
                category="LLM08",
                name="Vector and Embedding Weaknesses",
                priority=7,
                budget=5,
                status="scheduled",
                reason="RAG presence undetermined; running exploratory vector checks under safe-fallback policy.",
            )

    @classmethod
    def _plan_llm01(cls, profile: TargetProfile) -> CategoryPlan:
        """
        Prompt Injection Rule:
        - Prioritize higher if RAG is present (indirect prompt injection opportunity).
        """
        priority = 1 if profile.has_rag.detected else 2
        reason = (
            "RAG detected: scheduling indirect document injection alongside direct injection."
            if profile.has_rag.detected
            else "Baseline direct prompt injection assessment."
        )
        return CategoryPlan(
            category="LLM01",
            name="Prompt Injection",
            priority=priority,
            budget=10,
            status="scheduled",
            reason=reason,
        )

    @classmethod
    def _plan_llm07(cls, profile: TargetProfile) -> CategoryPlan:
        """System Prompt Leakage Rule."""
        priority = 2
        if profile.site_type.value == "customer_support":
            priority = 1
        return CategoryPlan(
            category="LLM07",
            name="System Prompt Leakage",
            priority=priority,
            budget=10,
            status="scheduled",
            reason=f"Verifying system instructions and confidentiality boundaries for {profile.site_type.value}.",
        )

    @classmethod
    def _plan_llm03(cls, profile: TargetProfile) -> CategoryPlan:
        """
        Tool Agency Rule:
        - If tools detected: Priority 1.
        - Else: Priority 5.
        """
        priority = 1 if profile.has_tools.detected else 5
        reason = (
            "External tools/APIs detected: prioritizing Excessive Agency testing."
            if profile.has_tools.detected
            else "Baseline Excessive Agency assessment."
        )
        return CategoryPlan(
            category="LLM03",
            name="Excessive Agency",
            priority=priority,
            budget=10,
            status="scheduled",
            reason=reason,
        )

    @classmethod
    def _plan_llm10(cls, profile: TargetProfile) -> CategoryPlan:
        """
        Output Handling Rule:
        - If HTML rendered: Priority 2 (XSS / tag injection).
        - If Markdown: Priority 4.
        - Else: Priority 6.
        """
        if profile.renders_html.detected:
            priority = 2
            reason = "HTML tag rendering detected: prioritizing Cross-Site Scripting (XSS) and tag injection tests."
        elif profile.renders_markdown.detected:
            priority = 4
            reason = "Markdown rendering detected: testing image exfiltration and link injection."
        else:
            priority = 6
            reason = "Standard output sanitization checks."

        return CategoryPlan(
            category="LLM10",
            name="Improper Output Handling",
            priority=priority,
            budget=10,
            status="scheduled",
            reason=reason,
        )

    @classmethod
    def _plan_llm02(cls, profile: TargetProfile) -> CategoryPlan:
        """Sensitive Information Disclosure Rule."""
        return CategoryPlan(
            category="LLM02",
            name="Sensitive Information Disclosure",
            priority=3,
            budget=10,
            status="scheduled",
            reason="Testing for leakage of credentials, PII, and internal configurations.",
        )

