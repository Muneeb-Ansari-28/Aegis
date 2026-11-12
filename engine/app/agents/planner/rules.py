"""Deterministic Test Planner Rule Engine (Step 0b).

Converts a TargetProfile into a prioritized, bounded TestPlan
using non-LLM Python logic and the 'Unknown ≠ Absent' safe-fallback policy.
"""
import hashlib
import json
import logging
from typing import List, Literal

from app.agents.planner.category_catalog import get_category_catalog
from app.agents.planner.prompt_filter import PromptMetadataFilter
from app.recon.schemas import TargetProfile
from app.schemas.test_plan import CategoryPlan, TestPlan

logger = logging.getLogger(__name__)


def calculate_plan_revision(profile: TargetProfile, categories: List[CategoryPlan]) -> str:
    """Compute a deterministic revision identifier suitable for stale-request detection."""
    payload = {
        "profile": profile.model_dump(mode="json"),
        "categories": [category.model_dump(mode="json") for category in categories],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class TestPlanner:
    """
    Translates TargetProfile capabilities into an actionable, bounded TestPlan.
    100% deterministic, non-LLM control plane.
    """

    @classmethod
    def build_test_plan(cls, profile: TargetProfile) -> TestPlan:
        """
        Synthesize prioritized categories and attempt budgets from the TargetProfile
        for all ten canonical OWASP GenAI 2026 categories.
        """
        catalog = get_category_catalog()
        categories: List[CategoryPlan] = []

        for cat_def in catalog:
            if cat_def.id == "LLM08":
                plan = cls._plan_llm08(profile, cat_def)
            elif cat_def.id == "LLM09":
                plan = cls._plan_llm09(profile, cat_def)
            elif cat_def.id == "LLM03":
                plan = cls._plan_llm03(profile, cat_def)
            elif cat_def.id == "LLM10":
                plan = cls._plan_llm10(profile, cat_def)
            elif cat_def.id == "LLM01":
                plan = cls._plan_llm01(profile, cat_def)
            elif cat_def.id == "LLM02":
                plan = cls._plan_llm02(profile, cat_def)
            else:
                plan = cls._plan_under_development(profile, cat_def)

            # Only assign prompts to selectable implemented categories
            if plan.selectable:
                prompt_ids = PromptMetadataFilter.get_applicable_prompts(
                    category=plan.category,
                    profile=profile,
                )
                plan.planned_prompt_ids = prompt_ids
                plan.applicable_prompt_ids = list(prompt_ids)
            else:
                plan.planned_prompt_ids = []
                plan.applicable_prompt_ids = []

            categories.append(plan)

        required_stages = ("tier1_passive", "active_probes", "classifier")
        is_complete = all(
            profile.stages.get(stage) is not None
            and profile.stages[stage].status == "completed"
            for stage in required_stages
        )
        if not is_complete:
            for category in categories:
                if category.selectable:
                    category.selectable = False
                    category.status = "not_tested"
                    category.testability = "partial"
                    category.budget = 0
                    category.planned_prompt_ids = []
                    category.applicable_prompt_ids = []
                    category.reason = (
                        "Recon is incomplete. Complete passive collection, active probes, "
                        "and classification before selecting scan categories."
                    )

        selectable_ids = [c.category for c in categories if c.selectable]
        total_budget = sum(c.budget for c in categories if c.selectable)
        plan_revision = calculate_plan_revision(profile, categories)

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
            selectable_category_ids=selectable_ids,
            plan_revision=plan_revision,
            is_complete=is_complete,
        )

    @classmethod
    def _plan_llm08(cls, profile: TargetProfile, cat_def) -> CategoryPlan:
        """
        LLM08: Hidden Context Exposure (Canonical 2026).
        Active, implemented evaluation pipeline for direct instruction disclosure and canaries.
        """
        priority = 1 if profile.site_type.value == "customer_support" else 2
        return CategoryPlan(
            category="LLM08",
            name=cat_def.name,
            priority=priority,
            budget=10,
            status="scheduled",
            implementation_status="implemented",
            testability="ready",
            applicability="applicable",
            selectable=True,
            reason=f"Active assessment scope: testing system instructions and confidentiality boundaries for {profile.site_type.value}.",
        )

    @classmethod
    def _plan_llm09(cls, profile: TargetProfile, cat_def) -> CategoryPlan:
        """
        LLM09: Vector and Embedding Weaknesses (Canonical 2026).
        RAG Rule:
        - If RAG detected (conf >= 0.6): applicable, priority 1.
        - If affirmative proof of NO RAG (conf >= 0.85): not_applicable.
        - Else (unknown): unknown (unknown != absent).
        Implementation status is currently under development.
        """
        applicability: Literal["applicable", "not_applicable", "unknown"]
        status: Literal["scheduled", "not_applicable", "not_tested"]
        if profile.has_rag.detected and profile.has_rag.confidence >= 0.6:
            applicability = "applicable"
            status = "not_tested"
            reason = f"RAG architecture detected ({profile.has_rag.source}, conf={profile.has_rag.confidence}): pipeline under development."
            priority = 1
        elif not profile.has_rag.detected and profile.has_rag.confidence >= 0.85:
            applicability = "not_applicable"
            status = "not_applicable"
            reason = "Not applicable (recon: affirmative proof of no RAG / vector embeddings)."
            priority = 10
        else:
            applicability = "unknown"
            status = "not_tested"
            reason = "RAG presence undetermined (unknown is not absent); category pipeline under development."
            priority = 7

        return CategoryPlan(
            category="LLM09",
            name=cat_def.name,
            priority=priority,
            budget=0,
            status=status,
            implementation_status="under_development",
            testability="not_tested",
            applicability=applicability,
            selectable=False,
            reason=reason,
        )

    @classmethod
    def _plan_llm03(cls, profile: TargetProfile, cat_def) -> CategoryPlan:
        """LLM03: Excessive Agency. Tool Agency Rule."""
        applicability: Literal["applicable", "not_applicable", "unknown"]
        status: Literal["scheduled", "not_applicable", "not_tested"]
        if profile.has_tools.detected:
            applicability = "applicable"
            reason = "Active assessment scope: external tools/APIs detected; testing tool execution and privilege boundaries."
            priority = 1
            selectable = True
            status = "scheduled"
            budget = 6
        elif not profile.has_tools.detected and profile.has_tools.confidence >= 0.85:
            applicability = "not_applicable"
            reason = "Not applicable (recon: affirmative proof target does not expose external tools)."
            priority = 10
            selectable = False
            status = "not_applicable"
            budget = 0
        else:
            applicability = "unknown"
            reason = "Tool agency presence undetermined; external tools required to evaluate excessive agency."
            priority = 5
            selectable = False
            status = "not_tested"
            budget = 0

        return CategoryPlan(
            category="LLM03",
            name=cat_def.name,
            priority=priority,
            budget=budget,
            status=status,
            implementation_status="implemented",
            testability="ready" if selectable else "not_tested",
            applicability=applicability,
            selectable=selectable,
            reason=reason,
        )

    @classmethod
    def _plan_llm10(cls, profile: TargetProfile, cat_def) -> CategoryPlan:
        """LLM10: Improper Output Handling. Rendering Rule."""
        applicability: Literal["applicable", "not_applicable", "unknown"]
        if profile.renders_html.detected:
            priority = 2
            reason = "Active assessment scope: HTML rendering detected; testing output sanitization and markup injection."
            applicability = "applicable"
        elif profile.renders_markdown.detected:
            priority = 4
            reason = "Active assessment scope: Markdown rendering detected; testing tracking pixel and link injection."
            applicability = "applicable"
        else:
            priority = 6
            reason = "Active assessment scope: testing output sanitization and hyperlink formatting."
            applicability = "applicable"

        return CategoryPlan(
            category="LLM10",
            name=cat_def.name,
            priority=priority,
            budget=4,
            status="scheduled",
            implementation_status="implemented",
            testability="ready",
            applicability=applicability,
            selectable=True,
            reason=reason,
        )

    @classmethod
    def _plan_llm01(cls, profile: TargetProfile, cat_def) -> CategoryPlan:
        """LLM01: Prompt Injection. Active implemented assessment scope."""
        priority = 1 if profile.has_rag.detected else 2
        return CategoryPlan(
            category="LLM01",
            name=cat_def.name,
            priority=priority,
            budget=8,
            status="scheduled",
            implementation_status="implemented",
            testability="ready",
            applicability="applicable",
            selectable=True,
            reason="Active assessment scope: testing instruction adherence and prompt injection safeguards.",
        )

    @classmethod
    def _plan_llm02(cls, profile: TargetProfile, cat_def) -> CategoryPlan:
        """LLM02: Sensitive Information Disclosure."""
        return CategoryPlan(
            category="LLM02",
            name=cat_def.name,
            priority=3,
            budget=0,
            status="not_tested",
            implementation_status="under_development",
            testability="not_tested",
            applicability="applicable",
            selectable=False,
            reason="Sensitive information disclosure testing pipeline under development.",
        )

    @classmethod
    def _plan_under_development(cls, profile: TargetProfile, cat_def) -> CategoryPlan:
        """Generic fallback for roadmap categories under active development."""
        return CategoryPlan(
            category=cat_def.id,
            name=cat_def.name,
            priority=8,
            budget=0,
            status="not_tested",
            implementation_status="under_development",
            testability="not_tested",
            applicability="applicable",
            selectable=False,
            reason=f"{cat_def.name} testing pipeline under development.",
        )
