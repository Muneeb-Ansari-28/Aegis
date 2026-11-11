"""Deterministic scan state machine with persistence and telemetry."""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.adapters.base import BaseAdapter
from app.agents.attack_agent import AttackAgent
from app.agents.evaluation.evaluator import Evaluator
from app.agents.risk_scorer import RiskScorer
from app.agents.state import ScanState
from app.core.database import SessionLocal
from app.core.events import event_bus
from app.models.entities import FindingEntity, ScanTurnEntity
from app.schemas.test_plan import CategoryPlan
from app.schemas.verdict import JudgeVerdict

logger = logging.getLogger(__name__)


class Orchestrator:
    """Run selected category plans sequentially and retain category-level results."""

    def __init__(
        self,
        scan_id: str,
        adapter: Optional[BaseAdapter] = None,
        max_budget: int = 10,
        session_factory=SessionLocal,
        category: str = "LLM08",
        applicable_prompt_ids: Optional[List[str]] = None,
        category_plans: Optional[List[CategoryPlan]] = None,
        adapter_factory: Optional[Callable[[], BaseAdapter]] = None,
        category_update_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ) -> None:
        """Create a scan runner with one or more server-approved category plans."""
        if category_plans:
            self.category_plans = [plan.model_copy(deep=True) for plan in category_plans]
        else:
            self.category_plans = [CategoryPlan(
                category=(category or "LLM08").upper(),
                name=(category or "LLM08").upper(),
                budget=max_budget,
                status="scheduled",
                implementation_status="implemented",
                testability="ready",
                applicability="applicable",
                selectable=True,
                planned_prompt_ids=list(applicable_prompt_ids or []),
            )]
        if not self.category_plans:
            raise ValueError("At least one category plan is required.")
        if adapter is None and adapter_factory is None:
            raise ValueError("An adapter or adapter factory is required.")

        self.scan_id = scan_id
        self.adapter = adapter
        self.adapter_factory = adapter_factory
        self.max_budget = sum(plan.budget for plan in self.category_plans)
        self.category = self.category_plans[0].category.upper()
        self.current_category = self.category
        self.state = ScanState.QUEUED
        self.attack_agent: Any = AttackAgent(
            category=self.category,
            applicable_prompt_ids=self.category_plans[0].planned_prompt_ids,
        )
        self.evaluator: Any = Evaluator()
        self._session_factory = session_factory
        self._category_update_callback = category_update_callback
        self._stop_requested = asyncio.Event()
        self.current_attempt = 0
        self.category_results: List[Dict[str, Any]] = [
            {
                "category": plan.category,
                "name": plan.name,
                "status": "QUEUED",
                "attempts": 0,
                "budget": plan.budget,
                "exploited": False,
                "error": None,
            }
            for plan in self.category_plans
        ]

    def stop(self) -> None:
        """Request that the scan stop at the next turn boundary."""
        self._stop_requested.set()

    async def _emit(self, event: str, **details: object) -> None:
        """Publish a scan lifecycle event to its telemetry channel."""
        await event_bus.publish(self.scan_id, {
            "scan_id": self.scan_id, "event": event, "status": self.state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(), **details,
        })

    def _persist_turn(self, turn, verdict) -> None:
        """Store a turn and, when exploited, its linked finding transactionally."""
        with self._session_factory() as session:
            cat = getattr(turn, "category", self.category) or self.category
            row = ScanTurnEntity(
                id=turn.turn_id or str(uuid.uuid4()), scan_id=self.scan_id,
                turn_index=turn.turn_index,
                category=cat,
                attempt_in_category=getattr(turn, "attempt_in_category", turn.turn_index) or turn.turn_index,
                prompt=turn.prompt, response=turn.response,
                latency_ms=turn.latency_ms, strategy=turn.strategy,
                verdict=verdict.model_dump(mode="json") if verdict else None,
                created_at=turn.timestamp,
            )
            session.add(row)
            if verdict and verdict.exploited:
                verdict_cat = verdict.category or cat
                severity = RiskScorer.compute_severity(verdict_cat, verdict.confidence)
                session.add(FindingEntity(
                    id=str(uuid.uuid4()), scan_id=self.scan_id, turn_id=row.id,
                    category=verdict_cat, severity=severity,
                    confidence=verdict.confidence, description=verdict.rationale,
                    remediation=f"Review boundaries and safeguards for OWASP {verdict_cat}.",
                ))
            session.commit()

    def _publish_category_results(self) -> None:
        if self._category_update_callback:
            self._category_update_callback([dict(item) for item in self.category_results])

    async def _run_category(self, plan: CategoryPlan, index: int) -> Optional[JudgeVerdict]:
        result = self.category_results[index]
        result["status"] = "RUNNING"
        result["name"] = plan.name
        self.current_category = plan.category
        if index > 0:
            self.attack_agent = AttackAgent(
                category=plan.category,
                applicable_prompt_ids=plan.planned_prompt_ids,
            )
            self.evaluator = Evaluator()
        self._publish_category_results()
        await self._emit("category_started", category=plan.category, budget=plan.budget)

        adapter = self.adapter_factory() if self.adapter_factory else self.adapter
        if adapter is None:
            raise RuntimeError("No adapter is configured for this category.")
        self.adapter = adapter
        category_verdict: Optional[JudgeVerdict] = None
        previous_feedback: Optional[str] = None
        result_status = "COMPLETED"
        try:
            await adapter.open()
            for attempt_in_category in range(1, plan.budget + 1):
                if self._stop_requested.is_set():
                    result_status = "STOPPED"
                    break
                prompt, strategy = await self.attack_agent.generate_prompt(
                    attempt_in_category, previous_feedback
                )
                self.current_attempt += 1
                await self._emit(
                    "turn_started",
                    attempt=self.current_attempt,
                    attempt_in_category=attempt_in_category,
                    budget=self.max_budget,
                    category=plan.category,
                    prompt=prompt,
                    strategy=strategy,
                )
                turn = await adapter.send_prompt(prompt, attempt_in_category)
                turn.scan_id = self.scan_id
                turn.turn_index = self.current_attempt
                turn.attempt_in_category = attempt_in_category
                turn.strategy = strategy
                turn.category = plan.category
                if turn.status != "success" and not turn.response.startswith("[CONNECTOR_"):
                    marker = "TIMEOUT" if turn.status == "timeout" else "ERROR"
                    turn.response = f"[CONNECTOR_{marker}] {turn.response}"
                category_verdict = await self.evaluator.evaluate(turn) if turn.status == "success" else None
                self._persist_turn(turn, category_verdict)
                result["attempts"] = attempt_in_category
                result["exploited"] = bool(category_verdict and category_verdict.exploited)
                await self._emit(
                    "turn_completed",
                    attempt=self.current_attempt,
                    attempt_in_category=attempt_in_category,
                    budget=self.max_budget,
                    category=plan.category,
                    prompt=turn.prompt,
                    response=turn.response,
                    latency_ms=turn.latency_ms,
                    status=turn.status,
                    strategy=turn.strategy,
                    verdict=category_verdict.model_dump(mode="json") if category_verdict else None,
                )
                if turn.status != "success":
                    result_status = "FAILED"
                    result["error"] = turn.metadata.get("error") or turn.response
                    break
                if category_verdict and category_verdict.exploited:
                    break
                previous_feedback = category_verdict.rationale if category_verdict else None
        except Exception as exc:
            logger.exception("Category %s failed in scan %s", plan.category, self.scan_id)
            result_status = "FAILED"
            result["error"] = str(exc)
        finally:
            try:
                await adapter.close()
            except Exception as exc:
                result_status = "FAILED"
                result["error"] = result.get("error") or f"Adapter close failed: {exc}"

        result["status"] = result_status
        self._publish_category_results()
        await self._emit(
            "category_completed",
            category=plan.category,
            status=result_status,
            attempts=result["attempts"],
            exploited=result["exploited"],
            error=result["error"],
        )
        return category_verdict if category_verdict and category_verdict.exploited else None

    async def run(self):
        """Execute every selected category and aggregate their terminal outcomes."""
        self.state = ScanState.RUNNING
        await self._emit(
            "scan_started",
            budget=self.max_budget,
            category=self.category,
            category_ids=[plan.category for plan in self.category_plans],
        )
        first_finding: Optional[JudgeVerdict] = None
        try:
            for index, plan in enumerate(self.category_plans):
                if self._stop_requested.is_set():
                    for remaining in self.category_results[index:]:
                        remaining["status"] = "STOPPED"
                    self._publish_category_results()
                    break
                verdict = await self._run_category(plan, index)
                if verdict and first_finding is None:
                    first_finding = verdict

            statuses = [result["status"] for result in self.category_results]
            if "STOPPED" in statuses:
                self.state = ScanState.STOPPED
            elif all(status == "COMPLETED" for status in statuses):
                self.state = ScanState.COMPLETED
            elif any(status == "COMPLETED" for status in statuses):
                self.state = ScanState.PARTIAL
            else:
                self.state = ScanState.FAILED

            terminal_event = {
                ScanState.COMPLETED: "scan_completed",
                ScanState.PARTIAL: "scan_partial",
                ScanState.STOPPED: "scan_stopped",
                ScanState.FAILED: "scan_failed",
            }[self.state]
            await self._emit(
                terminal_event,
                exploited=any(bool(result["exploited"]) for result in self.category_results),
                attempt=self.current_attempt,
                error="; ".join(
                    f"{item['category']}: {item['error']}"
                    for item in self.category_results
                    if item.get("error")
                ) or None,
                category_results=self.category_results,
            )
            return first_finding
        except Exception as exc:
            self.state = ScanState.FAILED
            await self._emit("scan_failed", attempt=self.current_attempt, error=str(exc))
            raise
