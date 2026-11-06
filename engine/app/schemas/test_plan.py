"""Test Plan Schema for the Deterministic Test Planner (Step 0b)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field


class CategoryPlan(BaseModel):
    """
    Plan definition for a specific OWASP category within a scan.
    """
    category: str                                 # OWASP category code (e.g. LLM01, LLM08)
    name: str                                     # Human readable vulnerability name
    priority: int = Field(ge=1, le=10)            # 1 (Highest) to 10 (Lowest)
    budget: int = Field(default=10, ge=0, le=20)  # Max prompt attempts allocated (N <= 10)
    status: Literal["scheduled", "not_applicable", "not_tested"] = "scheduled"
    reason: str = ""                              # Rationale for priority, scheduling, or skipping
    applicable_prompt_ids: List[str] = Field(default_factory=list)


class TestPlan(BaseModel):
    """
    Deterministic execution plan synthesized from the Target Profile.
    Directs the Orchestrator attack loop.
    """
    target_id: str
    target_profile_summary: Dict[str, Any] = Field(default_factory=dict)
    categories: List[CategoryPlan] = Field(default_factory=list)
    total_budget: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_scheduled_categories(self) -> List[CategoryPlan]:
        """Return scheduled categories sorted in execution order by priority."""
        return sorted(
            [c for c in self.categories if c.status == "scheduled"],
            key=lambda c: c.priority,
        )

