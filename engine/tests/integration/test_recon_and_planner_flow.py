"""End-to-End Integration Test for Recon Agent and Test Planner Pipeline."""
import pytest
import uuid
from typing import Optional
from pathlib import Path
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.base import BaseAdapter
from app.agents.planner.rules import TestPlanner
from app.core.database import Base
from app.models.entities import TargetEntity, ReconRunEntity, ReconTurnEntity
from app.recon.network_collector import PassiveReconData, ChatCandidates
from app.schemas.target import TargetCreate
from app.schemas.turn_record import TurnRecord
from app.services.recon_service import ReconService
from app.services.target_service import TargetService


@pytest.fixture
def mem_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory
    engine.dispose()


class MockTargetAdapter(BaseAdapter):
    """Simulates an interactive target with chat and memory responses."""
    def __init__(self):
        self.opened = False
        self.closed = False

    async def open(self) -> None:
        self.opened = True

    async def close(self) -> None:
        self.closed = True

    async def reset_session(self) -> None:
        pass

    async def send_prompt(
        self,
        prompt: str,
        attempt: int,
        scan_id: str = "test",
        strategy: Optional[str] = None,
        **kwargs,
    ) -> TurnRecord:
        reply = "I am a customer support agent for Acme Services."
        if strategy == "probe_mem_1":
            reply = "I will remember that your favorite color is AegisCyan42."
        elif strategy == "probe_mem_2":
            reply = "Your favorite color is AegisCyan42."
        elif strategy == "probe_render":
            reply = "Here is the text: <b>BoldTestMarker</b>"

        return TurnRecord(
            turn_id=str(uuid.uuid4()),
            scan_id=scan_id,
            turn_index=attempt,
            prompt=prompt,
            response=reply,
            strategy=strategy,
            status="success",
            latency_ms=45,
        )


@pytest.mark.asyncio
async def test_full_recon_to_test_plan_pipeline(tmp_path, mem_db):
    TargetService._targets.clear()

    # 1. Create a mock target project folder for Tier 3 static analysis
    project_dir = tmp_path / "acme_bot"
    project_dir.mkdir()
    (project_dir / "requirements.txt").write_text("fastapi\nchromadb\nuvicorn\n")
    (project_dir / ".env").write_text("PINECONE_API_KEY=test_val_9999\n")

    with patch("app.services.target_service.SessionLocal", mem_db), \
         patch("app.services.recon_service.SessionLocal", mem_db), \
         patch("app.recon.probe_runner.SessionLocal", mem_db):

        # 2. Register Target
        target = await TargetService.create_target(
            TargetCreate(
                name="Acme Bot Integration",
                target_type="web",
                url="http://localhost:8001",
                project_path=str(project_dir),
                calibration_config={"input_selector": "#input", "submit_selector": "#send", "response_selector": "#chat"},
            )
        )

        mock_passive = PassiveReconData(
            target_url=target.url or "",
            page_title="Acme Bot Portal",
            page_text_sample="Customer service and account questions.",
            observed_signals={
                "paths": ["/openapi.json", "/api/chat"],
                "headers": {"server": "uvicorn"},
                "dom": [],
                "globals": [],
                "scripts": [],
                "response_keys": ["citations"],
                "payload_keys": ["messages"],
                "websocket_paths": [],
            },
            chat_candidates=ChatCandidates(inputs=["#input"], submits=["#send"], responses=["#chat"]),
            well_known_found=["/openapi.json"],
        )

        mock_adapter = MockTargetAdapter()

        # Mock Playwright network collection and adapter initialization
        with patch("app.recon.network_collector.PassiveNetworkCollector.collect", new_callable=AsyncMock) as mock_col:
            mock_col.return_value = mock_passive
            with patch("app.services.recon_service.PlaywrightWebAdapter", return_value=mock_adapter):
                # 3. Execute Recon Agent (Step 0a)
                profile = await ReconService.run_recon(
                    target.id,
                    project_path=str(project_dir),
                    run_probes=True,
                    authorized=True,
                )

        # 4. Verify Target Profile Assertions
        assert profile.target_id == target.id
        # Tier 3 manifests (chromadb) + signature matches (citations) should corroborate RAG
        assert profile.has_rag.detected is True
        assert profile.has_rag.confidence >= 0.85
        assert profile.has_vector_db.detected is True
        assert profile.has_vector_db.value is not None and "ChromaDB" in profile.has_vector_db.value
        assert any("chromadb" in db.lower() for db in profile.has_vector_db.evidence)
        assert profile.has_conversation_memory.detected is True
        # Model text echoing HTML tags is not verified DOM HTML rendering
        assert profile.renders_html.detected is False

        # Verify that probe turns were persisted in recon_turns for this recon run
        with mem_db() as session:
            run_entity = (
                session.query(ReconRunEntity)
                .filter(ReconRunEntity.target_id == target.id)
                .first()
            )
            assert run_entity is not None
            assert run_entity.status == "COMPLETED"
            recon_turns = (
                session.query(ReconTurnEntity)
                .filter(ReconTurnEntity.recon_run_id == run_entity.id)
                .all()
            )
            assert len(recon_turns) == 6

        # 5. Execute Test Planner (Step 0b)
        test_plan = TestPlanner.build_test_plan(profile)

        assert test_plan.target_id == target.id
        assert test_plan.total_budget > 0
        assert len(test_plan.categories) == 10

        # Scheduled categories validation: Only implemented categories are scheduled/selectable
        scheduled_cats = [c.category for c in test_plan.get_scheduled_categories()]
        assert "LLM08" in scheduled_cats
        assert test_plan.selectable_category_ids == ["LLM08"]

        # Verify LLM08 is scheduled and ready
        llm08_plan = next(c for c in test_plan.categories if c.category == "LLM08")
        assert llm08_plan.priority == 1
        assert llm08_plan.status == "scheduled"
        assert llm08_plan.implementation_status == "implemented"
        assert llm08_plan.selectable is True
        assert len(llm08_plan.applicable_prompt_ids) > 0

        # Verify under-development categories remain not_tested and unselectable
        llm01_plan = next(c for c in test_plan.categories if c.category == "LLM01")
        assert llm01_plan.implementation_status == "under_development"
        assert llm01_plan.selectable is False
        assert len(llm01_plan.applicable_prompt_ids) == 0

        llm09_plan = next(c for c in test_plan.categories if c.category == "LLM09")
        assert llm09_plan.implementation_status == "under_development"
        assert llm09_plan.selectable is False
