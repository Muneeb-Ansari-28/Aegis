"""Unit tests for Deterministic Test Planner and Safe-Fallback Rules."""
import pytest
from app.agents.planner.rules import TestPlanner
from app.agents.planner.prompt_filter import PromptMetadataFilter
from app.recon.schemas import FieldEvidence, TargetProfile


def make_profile(
    has_rag: bool = False,
    rag_conf: float = 0.4,
    has_tools: bool = False,
    tools_conf: float = 0.4,
    renders_html: bool = False,
) -> TargetProfile:
    return TargetProfile(
        target_id="test-target-1",
        target_url="http://localhost:8000",
        site_type=FieldEvidence(detected=True, value="customer_support", confidence=0.8),
        has_rag=FieldEvidence(detected=has_rag, confidence=rag_conf),
        has_tools=FieldEvidence(detected=has_tools, confidence=tools_conf),
        renders_html=FieldEvidence(detected=renders_html, confidence=0.8 if renders_html else 0.4),
    )


def test_planner_schedules_rag_when_detected():
    profile = make_profile(has_rag=True, rag_conf=0.85)
    plan = TestPlanner.build_test_plan(profile)

    llm08 = next(c for c in plan.categories if c.category == "LLM08")
    assert llm08.status == "scheduled"
    assert llm08.priority == 1
    assert llm08.budget == 10

    llm01 = next(c for c in plan.categories if c.category == "LLM01")
    assert llm01.priority == 1
    assert "indirect" in llm01.reason.lower()


def test_planner_marks_not_applicable_on_affirmative_no_rag():
    # Affirmative proof of no RAG (confidence >= 0.85)
    profile = make_profile(has_rag=False, rag_conf=0.90)
    plan = TestPlanner.build_test_plan(profile)

    llm08 = next(c for c in plan.categories if c.category == "LLM08")
    assert llm08.status == "not_applicable"
    assert llm08.budget == 0
    assert "no rag detected" in llm08.reason.lower()


def test_planner_safe_fallback_on_unknown_rag():
    # RAG not detected, but confidence is low (unknown != absent)
    profile = make_profile(has_rag=False, rag_conf=0.40)
    plan = TestPlanner.build_test_plan(profile)

    llm08 = next(c for c in plan.categories if c.category == "LLM08")
    # Must NOT be marked not_applicable! Safe-fallback schedules it with reduced budget
    assert llm08.status == "scheduled"
    assert llm08.budget == 5
    assert "safe-fallback" in llm08.reason.lower()


def test_planner_prioritizes_tools_and_html():
    profile = make_profile(has_tools=True, tools_conf=0.85, renders_html=True)
    plan = TestPlanner.build_test_plan(profile)

    llm03 = next(c for c in plan.categories if c.category == "LLM03")
    assert llm03.priority == 1
    assert "tools/apis detected" in llm03.reason.lower()

    llm10 = next(c for c in plan.categories if c.category == "LLM10")
    assert llm10.priority == 2
    assert "html tag rendering detected" in llm10.reason.lower()


def test_prompt_metadata_filter_requires_conditions():
    rag_profile = make_profile(has_rag=True, rag_conf=0.9)
    no_rag_profile = make_profile(has_rag=False, rag_conf=0.9)

    prompts_rag = PromptMetadataFilter.get_applicable_prompts("LLM08", rag_profile)
    # When RAG is detected, LLM08 prompts should be applicable
    assert len(prompts_rag) > 0

    prompts_no_rag = PromptMetadataFilter.get_applicable_prompts("LLM08", no_rag_profile)
    # When RAG is not detected, prompts requiring has_rag=true must NOT match
    assert len(prompts_no_rag) == 0

