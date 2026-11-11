"""Unit tests for Deterministic Test Planner and Safe-Fallback Rules."""
import pytest
from app.agents.planner.rules import TestPlanner, calculate_plan_revision
from app.agents.planner.prompt_filter import PromptMetadataFilter
from app.recon.schemas import FieldEvidence, ReconStageDetail, TargetProfile


def make_profile(
    has_rag: bool = False,
    rag_conf: float = 0.4,
    has_tools: bool = False,
    tools_conf: float = 0.4,
    renders_html: bool = False,
    site_type: str = "customer_support",
) -> TargetProfile:
    return TargetProfile(
        target_id="test-target-1",
        target_url="http://localhost:8000",
        site_type=FieldEvidence(detected=True, value=site_type, confidence=0.8),
        has_rag=FieldEvidence(detected=has_rag, confidence=rag_conf),
        has_tools=FieldEvidence(detected=has_tools, confidence=tools_conf),
        renders_html=FieldEvidence(detected=renders_html, confidence=0.8 if renders_html else 0.4),
        stages={
            "tier1_passive": ReconStageDetail(status="completed"),
            "active_probes": ReconStageDetail(status="completed"),
            "classifier": ReconStageDetail(status="completed"),
        },
    )


def test_planner_contains_all_ten_categories():
    profile = make_profile()
    plan = TestPlanner.build_test_plan(profile)

    assert len(plan.categories) == 10
    cat_ids = [c.category for c in plan.categories]
    assert cat_ids == [
        "LLM01", "LLM02", "LLM03", "LLM04", "LLM05",
        "LLM06", "LLM07", "LLM08", "LLM09", "LLM10",
    ]


def test_planner_schedules_llm08_hidden_context_exposure():
    profile = make_profile(site_type="customer_support")
    plan = TestPlanner.build_test_plan(profile)

    llm08 = next(c for c in plan.categories if c.category == "LLM08")
    assert llm08.name == "Hidden Context Exposure"
    assert llm08.status == "scheduled"
    assert llm08.implementation_status == "implemented"
    assert llm08.testability == "ready"
    assert llm08.applicability == "applicable"
    assert llm08.selectable is True
    assert llm08.budget == 10
    assert llm08.priority == 1
    assert len(llm08.planned_prompt_ids) > 0


def test_planner_evaluates_rag_on_llm09():
    # 1. RAG detected
    rag_profile = make_profile(has_rag=True, rag_conf=0.85)
    plan_rag = TestPlanner.build_test_plan(rag_profile)
    llm09 = next(c for c in plan_rag.categories if c.category == "LLM09")
    assert llm09.name == "Vector and Embedding Weaknesses"
    assert llm09.applicability == "applicable"
    assert llm09.priority == 1
    assert llm09.implementation_status == "under_development"
    assert llm09.selectable is False

    # 2. Affirmative proof of no RAG
    no_rag_profile = make_profile(has_rag=False, rag_conf=0.90)
    plan_no_rag = TestPlanner.build_test_plan(no_rag_profile)
    llm09_no = next(c for c in plan_no_rag.categories if c.category == "LLM09")
    assert llm09_no.applicability == "not_applicable"
    assert llm09_no.status == "not_applicable"
    assert llm09_no.budget == 0

    # 3. Unknown RAG (conf < 0.6): unknown != absent
    unknown_profile = make_profile(has_rag=False, rag_conf=0.40)
    plan_unk = TestPlanner.build_test_plan(unknown_profile)
    llm09_unk = next(c for c in plan_unk.categories if c.category == "LLM09")
    assert llm09_unk.applicability == "unknown"
    assert llm09_unk.status == "not_tested"
    assert "unknown is not absent" in llm09_unk.reason.lower()


def test_planner_prioritizes_tools_and_html():
    profile = make_profile(has_tools=True, tools_conf=0.85, renders_html=True)
    plan = TestPlanner.build_test_plan(profile)

    llm03 = next(c for c in plan.categories if c.category == "LLM03")
    assert llm03.name == "Excessive Agency"
    assert llm03.priority == 1
    assert llm03.applicability == "applicable"
    assert "tools" in llm03.reason.lower()

    llm10 = next(c for c in plan.categories if c.category == "LLM10")
    assert llm10.name == "Improper Output Handling"
    assert llm10.priority == 2
    assert llm10.applicability == "applicable"
    assert "html" in llm10.reason.lower()


def test_plan_revision_is_deterministic_and_dynamic():
    profile1 = make_profile(has_rag=True, rag_conf=0.9)
    profile2 = make_profile(has_rag=False, rag_conf=0.9)

    plan1 = TestPlanner.build_test_plan(profile1)
    plan1_again = TestPlanner.build_test_plan(profile1)
    plan2 = TestPlanner.build_test_plan(profile2)

    assert plan1.plan_revision != ""
    assert plan1.plan_revision == plan1_again.plan_revision
    assert plan1.plan_revision != plan2.plan_revision


def test_plan_revision_changes_when_executable_prompt_set_changes():
    profile = make_profile()
    plan = TestPlanner.build_test_plan(profile)
    original = calculate_plan_revision(profile, plan.categories)
    plan.categories[-3].planned_prompt_ids.append("new-eligible-prompt")

    assert calculate_plan_revision(profile, plan.categories) != original


def test_planner_marks_failed_required_recon_incomplete():
    profile = make_profile()
    profile.stages = {
        "tier1_passive": ReconStageDetail(status="failed", warning="navigation failed"),
        "active_probes": ReconStageDetail(status="skipped"),
        "classifier": ReconStageDetail(status="failed", warning="classifier unavailable"),
    }

    plan = TestPlanner.build_test_plan(profile)

    assert plan.is_complete is False


def test_selectable_categories_restricted_to_implemented():
    profile = make_profile(has_rag=True, has_tools=True, renders_html=True)
    plan = TestPlanner.build_test_plan(profile)

    # Only implemented categories with complete pipelines can be selectable
    assert plan.selectable_category_ids == ["LLM08"]
    selectable = plan.get_selectable_categories()
    assert len(selectable) == 1
    assert selectable[0].category == "LLM08"


def test_prompt_metadata_filter_requires_and_applicable_when():
    rag_profile = make_profile(has_rag=True, rag_conf=0.9)
    no_rag_profile = make_profile(has_rag=False, rag_conf=0.9)

    # LLM08 disclosure prompts (should be available on any general assistant profile)
    prompts_llm08 = PromptMetadataFilter.get_applicable_prompts("LLM08", rag_profile)
    assert len(prompts_llm08) > 0
    assert not any(token in prompt_id for prompt_id in prompts_llm08 for token in ("roleplay", "encoding", "creative", "authority", "distraction"))

    # Test applicable_when evaluator directly
    assert PromptMetadataFilter._matches_applicable_when("has_rag", rag_profile) is True
    assert PromptMetadataFilter._matches_applicable_when("has_rag", no_rag_profile) is False
    assert PromptMetadataFilter._matches_applicable_when("not has_rag", no_rag_profile) is True
    assert PromptMetadataFilter._matches_applicable_when("true", rag_profile) is True
    assert PromptMetadataFilter._matches_applicable_when(None, rag_profile) is True
