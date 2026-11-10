from typing import Optional
import pytest
from app.agents.attack_agent import AttackAgent
from app.agents.orchestrator import Orchestrator
from app.adapters.base import BaseAdapter
from app.schemas.turn_record import TurnRecord


class DummyAdapter(BaseAdapter):
    async def open(self) -> None: pass

    async def send_prompt(
        self,
        prompt: str,
        attempt: int,
        scan_id: str = "scan-default",
        strategy: Optional[str] = None,
        **kwargs,
    ) -> TurnRecord:
        return TurnRecord(
            turn_id=f"t-{attempt}", scan_id=scan_id, turn_index=attempt,
            prompt=prompt, response="Refusal: I cannot fulfill this request.",
            status="success", latency_ms=10, strategy=strategy,
        )

    async def reset_session(self) -> None: pass
    async def close(self) -> None: pass


@pytest.mark.asyncio
async def test_attack_agent_category_prompt_selection():
    # 1. LLM01 - Prompt Injection
    agent_llm01 = AttackAgent(category="LLM01")
    prompt_01, _ = await agent_llm01.generate_prompt(turn_index=1)
    assert any(k in prompt_01.lower() for k in ["ignore", "instruction", "prompt_injection", "override"])

    # 2. LLM03 - Excessive Agency
    agent_llm03 = AttackAgent(category="LLM03")
    prompt_03, _ = await agent_llm03.generate_prompt(turn_index=1)
    assert any(k in prompt_03.lower() for k in ["tool", "whoami", "database", "file", "command"])

    # 3. LLM07 - System Prompt Disclosure
    agent_llm07 = AttackAgent(category="LLM07")
    prompt_07, _ = await agent_llm07.generate_prompt(turn_index=1)
    assert any(k in prompt_07.lower() for k in ["system", "instruction", "canary", "verbatim"])

    # 4. LLM08 - Hidden Context Exposure
    agent_llm08 = AttackAgent(category="LLM08")
    prompt_08, _ = await agent_llm08.generate_prompt(turn_index=1)
    assert any(k in prompt_08.lower() for k in ["context", "chunk", "document", "knowledge", "vector"])

    # 5. LLM10 - Improper Output Handling
    agent_llm10 = AttackAgent(category="LLM10")
    prompt_10, _ = await agent_llm10.generate_prompt(turn_index=1)
    assert any(k in prompt_10.lower() for k in ["markdown", "image", "pixel", "telemetry", "link", "html"])


@pytest.mark.asyncio
async def test_orchestrator_initializes_with_selected_category():
    adapter = DummyAdapter()
    for category in ["LLM01", "LLM03", "LLM07", "LLM08", "LLM10"]:
        orch = Orchestrator(scan_id=f"scan-{category}", adapter=adapter, max_budget=2, category=category)
        assert orch.category == category
        assert orch.attack_agent.category == category
        prompt, _ = await orch.attack_agent.generate_prompt(turn_index=1)
        assert len(prompt) > 0

