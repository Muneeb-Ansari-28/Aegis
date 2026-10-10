"""
Deterministic Orchestrator State Machine.
Controls scan budget, retry loop, and stops on exploit detection.
"""
import logging
from app.agents.state import ScanState
from app.agents.attack_agent import AttackAgent
from app.agents.evaluation.evaluator import Evaluator
from app.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, scan_id: str, adapter: BaseAdapter, max_budget: int = 10):
        self.scan_id = scan_id
        self.adapter = adapter
        self.max_budget = max_budget
        self.state = ScanState.QUEUED
        self.attack_agent = AttackAgent()
        self.evaluator = Evaluator()

    async def run(self):
        """Execute deterministic red-teaming loop."""
        self.state = ScanState.RUNNING
        logger.info(f"Starting scan {self.scan_id} with budget {self.max_budget}")
        
        await self.adapter.open()
        turn_index = 1
        previous_feedback = None

        try:
            while turn_index <= self.max_budget and self.state == ScanState.RUNNING:
                # 1. Generate attack prompt
                prompt, strategy = await self.attack_agent.generate_prompt(
                    turn_index=turn_index,
                    previous_feedback=previous_feedback
                )

                # 2. Transmit via target adapter
                turn_record = await self.adapter.send_prompt(prompt, turn_index)
                turn_record.strategy = strategy

                # 3. Evaluate response
                verdict = await self.evaluator.evaluate(turn_record)

                if verdict.exploited:
                    logger.info(f"Exploit confirmed at turn {turn_index}! Stopping scan.")
                    self.state = ScanState.COMPLETED
                    return verdict

                previous_feedback = verdict.rationale
                turn_index += 1

            self.state = ScanState.COMPLETED
            logger.info("Budget exhausted without confirmed exploit.")
            return None
        finally:
            await self.adapter.close()
