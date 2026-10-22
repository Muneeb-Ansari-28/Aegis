"""Deterministic scan state machine with persistence and telemetry."""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.adapters.base import BaseAdapter
from app.agents.attack_agent import AttackAgent
from app.agents.evaluation.evaluator import Evaluator
from app.agents.risk_scorer import RiskScorer
from app.agents.state import ScanState
from app.core.database import SessionLocal
from app.core.events import event_bus
from app.models.entities import FindingEntity, ScanTurnEntity

logger = logging.getLogger(__name__)


class Orchestrator:
    """Run a bounded scan and persist each turn and confirmed finding."""

    def __init__(self, scan_id: str, adapter: BaseAdapter, max_budget: int = 10,
                 session_factory=SessionLocal) -> None:
        """Create a scan runner with its adapter, budget, and DB session factory."""
        self.scan_id = scan_id
        self.adapter = adapter
        self.max_budget = max_budget
        self.state = ScanState.QUEUED
        self.attack_agent: Any = AttackAgent()
        self.evaluator: Any = Evaluator()
        self._session_factory = session_factory
        self._stop_requested = asyncio.Event()
        self.current_attempt = 0

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
            row = ScanTurnEntity(
                id=turn.turn_id or str(uuid.uuid4()), scan_id=self.scan_id,
                turn_index=turn.turn_index, prompt=turn.prompt, response=turn.response,
                latency_ms=turn.latency_ms, strategy=turn.strategy,
                verdict=verdict.model_dump(mode="json") if verdict else None,
                created_at=turn.timestamp,
            )
            session.add(row)
            if verdict and verdict.exploited:
                severity = RiskScorer.compute_severity(verdict.category, verdict.confidence)
                session.add(FindingEntity(
                    id=str(uuid.uuid4()), scan_id=self.scan_id, turn_id=row.id,
                    category=verdict.category, severity=severity,
                    confidence=verdict.confidence, description=verdict.rationale,
                    remediation="Review system prompt boundaries and remove sensitive instructions from model context.",
                ))
            session.commit()

    async def run(self):
        """Execute the scan until exploit, budget exhaustion, stop, or failure."""
        self.state = ScanState.RUNNING
        await self._emit("scan_started", budget=self.max_budget)
        previous_feedback: Optional[str] = None
        verdict = None
        try:
            await self.adapter.open()
            for turn_index in range(1, self.max_budget + 1):
                if self._stop_requested.is_set():
                    self.state = ScanState.STOPPED
                    break
                self.current_attempt = turn_index
                prompt, strategy = await self.attack_agent.generate_prompt(turn_index, previous_feedback)
                await self._emit(
                    "turn_started",
                    attempt=turn_index,
                    budget=self.max_budget,
                    category="LLM08",
                    prompt=prompt,
                    strategy=strategy,
                )
                turn = await self.adapter.send_prompt(prompt, turn_index)
                turn.scan_id = self.scan_id
                turn.strategy = strategy
                if turn.status != "success" and not turn.response.startswith("[CONNECTOR_"):
                    # Preserve status in the existing diagnostic text column; no
                    # schema migration is needed to replay failed turns.
                    marker = "TIMEOUT" if turn.status == "timeout" else "ERROR"
                    turn.response = f"[CONNECTOR_{marker}] {turn.response}"
                # Connector failures contain diagnostics, not chatbot evidence.
                verdict = await self.evaluator.evaluate(turn) if turn.status == "success" else None
                self._persist_turn(turn, verdict)
                await self._emit(
                    "turn_completed",
                    attempt=turn_index,
                    budget=self.max_budget,
                    category="LLM08",
                    prompt=turn.prompt,
                    response=turn.response,
                    latency_ms=turn.latency_ms,
                    status=turn.status,
                    strategy=turn.strategy,
                    verdict=verdict.model_dump(mode="json") if verdict else None,
                )
                if turn.status != "success":
                    self.state = ScanState.FAILED
                    await self._emit("scan_failed", attempt=self.current_attempt,
                                     error=turn.metadata.get("error") or turn.response)
                    return None
                if verdict is not None and verdict.exploited:
                    self.state = ScanState.COMPLETED
                    break
                previous_feedback = verdict.rationale if verdict is not None else None
            else:
                self.state = ScanState.COMPLETED
            if self.state == ScanState.STOPPED:
                await self._emit("scan_stopped", attempt=self.current_attempt)
            else:
                await self._emit("scan_completed", exploited=bool(verdict and verdict.exploited), attempt=self.current_attempt)
            return verdict if verdict and verdict.exploited else None
        except Exception as exc:
            self.state = ScanState.FAILED
            await self._emit("scan_failed", attempt=self.current_attempt, error=str(exc))
            raise
        finally:
            try:
                await self.adapter.close()
            finally:
                if self.state == ScanState.RUNNING:
                    self.state = ScanState.COMPLETED
