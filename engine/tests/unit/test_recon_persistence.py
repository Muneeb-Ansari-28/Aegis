"""Unit tests for Recon Run identity and evidence persistence (Task 11).

Tests:
- Recon probe turns are linked to a real ReconRunEntity, not synthetic orphan scan IDs.
- Two consecutive recon runs for the same target have distinct identities and evidence attribution.
- Recon turns never appear in scan turns or findings.
"""
from datetime import datetime, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.base import BaseAdapter
from app.core.database import Base
from app.models.entities import ReconRunEntity, ReconTurnEntity, ScanEntity, ScanTurnEntity, TargetEntity
from app.recon.probe_runner import ProbeRunner
from app.schemas.turn_record import TurnRecord


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory
    engine.dispose()


@pytest.mark.asyncio
async def test_recon_turns_persisted_under_recon_run_not_synthetic_scan(mem_db):
    target_id = str(uuid.uuid4())
    run1_id = str(uuid.uuid4())

    with mem_db() as session:
        session.add(TargetEntity(id=target_id, name="Test", target_type="web"))
        session.add(ReconRunEntity(id=run1_id, target_id=target_id, status="COMPLETED"))
        session.commit()

    mock_adapter = MagicMock(spec=BaseAdapter)
    async def mock_send(prompt, attempt=1, scan_id=None, strategy=None):
        return TurnRecord(
            turn_id=f"turn-{attempt}",
            scan_id=run1_id,
            turn_index=attempt,
            category="RECON",
            prompt=prompt,
            response="Test reply",
            status="success",
        )
    mock_adapter.send_prompt = AsyncMock(side_effect=mock_send)

    runner = ProbeRunner(adapter=mock_adapter, recon_run_id=run1_id, session_factory=mem_db)
    await runner.run_probes(persist_turns=True)

    with mem_db() as session:
        # 1. Recon turns must be stored in recon_turns under run1_id
        r_turns = session.query(ReconTurnEntity).filter(ReconTurnEntity.recon_run_id == run1_id).all()
        assert len(r_turns) == 6

        # 2. No orphan turns should exist in scan_turns
        orphan_turns = session.query(ScanTurnEntity).all()
        assert len(orphan_turns) == 0


@pytest.mark.asyncio
async def test_two_recon_runs_separate_identities_and_turns(mem_db):
    target_id = str(uuid.uuid4())
    run1_id = str(uuid.uuid4())
    run2_id = str(uuid.uuid4())

    with mem_db() as session:
        session.add(TargetEntity(id=target_id, name="Target", target_type="web"))
        session.add(ReconRunEntity(id=run1_id, target_id=target_id, status="COMPLETED"))
        session.add(ReconRunEntity(id=run2_id, target_id=target_id, status="COMPLETED"))
        session.commit()

    mock_adapter = MagicMock(spec=BaseAdapter)
    async def mock_send(prompt, attempt=1, scan_id=None, strategy=None):
        return TurnRecord(
            turn_id=str(uuid.uuid4()),
            scan_id="irrelevant",
            turn_index=attempt,
            category="RECON",
            prompt=prompt,
            response="Hello",
            status="success",
        )
    mock_adapter.send_prompt = AsyncMock(side_effect=mock_send)

    runner1 = ProbeRunner(adapter=mock_adapter, recon_run_id=run1_id, session_factory=mem_db)
    await runner1.run_probes(persist_turns=True)

    runner2 = ProbeRunner(adapter=mock_adapter, recon_run_id=run2_id, session_factory=mem_db)
    await runner2.run_probes(persist_turns=True)

    with mem_db() as session:
        turns_run1 = session.query(ReconTurnEntity).filter(ReconTurnEntity.recon_run_id == run1_id).all()
        turns_run2 = session.query(ReconTurnEntity).filter(ReconTurnEntity.recon_run_id == run2_id).all()

        assert len(turns_run1) == 6
        assert len(turns_run2) == 6
        assert set(t.recon_run_id for t in turns_run1) == {run1_id}
        assert set(t.recon_run_id for t in turns_run2) == {run2_id}
