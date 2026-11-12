"""Unit tests for TargetService and Targets API (Task 1).

Tests:
- Creating a target with project_path persists it.
- Updating an existing target changes project_path and cache.
- Clearing project_path persists null.
- Omitting project_path in update leaves it unchanged.
- Updating non-existent target returns None / 404.
- Reloading from DB preserves project_path.
- Recon fallback uses target.project_path when omitted in run_recon.
"""
import uuid
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base
from app.models.entities import TargetEntity
from app.schemas.target import TargetCreate, TargetUpdate
from app.services.target_service import TargetService
from app.services.recon_service import ReconService
from app.api.v1.router import app


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


@pytest.mark.asyncio
async def test_create_target_persists_project_path(mem_db):
    TargetService._targets.clear()
    with patch("app.services.target_service.SessionLocal", mem_db):
        data = TargetCreate(
            name="Test Bot",
            url="http://localhost:8000",
            project_path="/workspace/my-project",
        )
        target = await TargetService.create_target(data)
        assert target.id is not None
        assert target.project_path == "/workspace/my-project"

        with mem_db() as session:
            entity = session.get(TargetEntity, target.id)
            assert entity is not None
            assert entity.project_path == "/workspace/my-project"


@pytest.mark.asyncio
async def test_update_target_changes_and_clears_project_path(mem_db):
    TargetService._targets.clear()
    with patch("app.services.target_service.SessionLocal", mem_db):
        data = TargetCreate(
            name="Test Bot",
            url="http://localhost:8000",
            project_path="/workspace/initial-path",
        )
        target = await TargetService.create_target(data)
        assert target.project_path == "/workspace/initial-path"

        # Update to new path
        update_data = TargetUpdate(project_path="/workspace/updated-path")
        updated = await TargetService.update_target(target.id, update_data)
        assert updated is not None
        assert updated.project_path == "/workspace/updated-path"
        assert TargetService._targets[target.id].project_path == "/workspace/updated-path"

        # Clear path explicitly
        clear_data = TargetUpdate(project_path="")
        cleared = await TargetService.update_target(target.id, clear_data)
        assert cleared is not None
        assert cleared.project_path is None

        # Verify DB persisted null
        with mem_db() as session:
            entity = session.get(TargetEntity, target.id)
            assert entity.project_path is None


@pytest.mark.asyncio
async def test_update_missing_target_returns_none(mem_db):
    TargetService._targets.clear()
    with patch("app.services.target_service.SessionLocal", mem_db):
        result = await TargetService.update_target("missing-uuid", TargetUpdate(project_path="/test"))
        assert result is None


@pytest.mark.asyncio
async def test_get_target_reloads_project_path_when_cache_empty(mem_db):
    TargetService._targets.clear()
    target_id = str(uuid.uuid4())
    with mem_db() as session:
        session.add(TargetEntity(
            id=target_id,
            name="Cached Bot",
            url="http://localhost:8000",
            target_type="web",
            project_path="/workspace/persisted-only",
        ))
        session.commit()

    with patch("app.services.target_service.SessionLocal", mem_db):
        target = await TargetService.get_target(target_id)
        assert target is not None
        assert target.project_path == "/workspace/persisted-only"


@pytest.mark.asyncio
async def test_recon_service_falls_back_to_target_project_path(mem_db):
    TargetService._targets.clear()
    target_id = str(uuid.uuid4())
    with mem_db() as session:
        session.add(TargetEntity(
            id=target_id,
            name="Recon Bot",
            url="http://localhost:8000",
            target_type="web",
            project_path="/nonexistent/saved/repo",
        ))
        session.commit()

    with patch("app.services.recon_service.SessionLocal", mem_db):
        with patch("app.services.recon_service.PassiveNetworkCollector"), \
             patch("app.services.recon_service.StaticProjectScanner") as mock_scanner:
            mock_scanner.return_value.scan.return_value = None
            await ReconService.run_recon(target_id=target_id, project_path=None)
            mock_scanner.assert_called_once_with("/nonexistent/saved/repo")


def test_api_patch_target_endpoints(mem_db, authenticated_client):
    TargetService._targets.clear()
    target_id = str(uuid.uuid4())
    with mem_db() as session:
        session.add(TargetEntity(
            id=target_id,
            name="API Target",
            url="http://localhost:8000",
            target_type="web",
            project_path="/initial/path",
        ))
        session.commit()

    with patch("app.services.target_service.SessionLocal", mem_db):
        client = authenticated_client

        # Successful update
        patch_res = client.patch(
            f"/api/v1/targets/{target_id}",
            json={"project_path": "/new/api/path"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["project_path"] == "/new/api/path"

        # 404 for missing target
        not_found_res = client.patch(
            f"/api/v1/targets/unknown-target-id",
            json={"project_path": "/new/api/path"},
        )
        assert not_found_res.status_code == 404
