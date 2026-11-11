"""Test Plan Schema for the Deterministic Test Planner (Step 0b)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field, model_validator


class CategoryPlan(BaseModel):
    """
    Plan definition for a specific OWASP category within a scan.
    """
    category: str                                 # OWASP category code (e.g. LLM01, LLM08)
    name: str                                     # Human readable vulnerability name
    priority: int = Field(default=5, ge=1, le=10) # 1 (Highest) to 10 (Lowest)
    budget: int = Field(default=10, ge=0, le=20)  # Max prompt attempts allocated (N <= 10)
    status: Literal["scheduled", "not_applicable", "not_tested"] = "scheduled"
    implementation_status: Literal["implemented", "under_development"] = "under_development"
    testability: Literal["ready", "partial", "not_testable", "not_tested"] = "not_tested"
    applicability: Literal["applicable", "not_applicable", "unknown"] = "unknown"
    selectable: bool = False
    reason: str = ""                              # Rationale for priority, scheduling, or skipping
    planned_prompt_ids: List[str] = Field(default_factory=list)
    applicable_prompt_ids: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_prompt_ids(self) -> "CategoryPlan":
        """Keep planned_prompt_ids and applicable_prompt_ids synchronized for backward compatibility."""
        if self.planned_prompt_ids and not self.applicable_prompt_ids:
            self.applicable_prompt_ids = list(self.planned_prompt_ids)
        elif self.applicable_prompt_ids and not self.planned_prompt_ids:
            self.planned_prompt_ids = list(self.applicable_prompt_ids)
        return self


class TestPlan(BaseModel):
    """
    Deterministic execution plan synthesized from the Target Profile.
    Directs the Orchestrator attack loop.
    """
    target_id: str
    target_profile_summary: Dict[str, Any] = Field(default_factory=dict)
    categories: List[CategoryPlan] = Field(default_factory=list)
    total_budget: int = 0
    selectable_category_ids: List[str] = Field(default_factory=list)
    plan_revision: str = ""
    is_complete: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def populate_derived_fields(self) -> "TestPlan":
        """Populate selectable_category_ids and total_budget if not explicitly provided."""
        if not self.selectable_category_ids:
            self.selectable_category_ids = [c.category for c in self.categories if c.selectable]
        if not self.total_budget:
            self.total_budget = sum(c.budget for c in self.categories if c.selectable or c.status == "scheduled")
        return self

    def get_scheduled_categories(self) -> List[CategoryPlan]:
        """Return scheduled categories sorted in execution order by priority."""
        return sorted(
            [c for c in self.categories if c.status == "scheduled"],
            key=lambda c: c.priority,
        )

    def get_selectable_categories(self) -> List[CategoryPlan]:
        """Return categories that are currently ready and implemented for execution."""
        return [c for c in self.categories if c.selectable]
