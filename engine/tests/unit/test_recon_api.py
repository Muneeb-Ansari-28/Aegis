"""Unit and integration tests for Recon and Test Plan API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.api.v1.router import app
from app.recon.schemas import FieldEvidence, TargetProfile


@pytest.fixture
def client():
    return TestClient(app)


def test_discover_local_dev_servers_endpoint(client):
    response = client.get("/api/v1/targets/local/discover")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_recon_and_plan_endpoints_lifecycle(client):
    # 1. Register a test target
    create_resp = client.post(
        "/api/v1/targets",
        json={
            "name": "Recon Test Target",
            "target_type": "web",
            "url": "http://localhost:8001",
        },
    )
    assert create_resp.status_code == 201
    target_id = create_resp.json()["id"]

    # Mock profile to avoid launching Playwright in this API unit test
    mock_profile = TargetProfile(
        target_id=target_id,
        target_url="http://localhost:8001",
        site_type=FieldEvidence(detected=True, value="customer_support", confidence=0.8),
        has_rag=FieldEvidence(detected=True, confidence=0.85, evidence=["Citations found"]),
        has_tools=FieldEvidence(detected=False, confidence=0.5),
        renders_html=FieldEvidence(detected=True, confidence=0.9),
    )

    with patch("app.services.recon_service.ReconService.run_recon", new_callable=AsyncMock) as mock_recon:
        mock_recon.return_value = mock_profile

        # 2. Trigger recon
        recon_resp = client.post(f"/api/v1/targets/{target_id}/recon")
        assert recon_resp.status_code == 200
        profile_data = recon_resp.json()
        assert profile_data["target_id"] == target_id
        assert profile_data["has_rag"]["detected"] is True

    # 3. Fetch saved profile
    with patch("app.services.recon_service.ReconService.get_target_profile") as mock_get_prof:
        mock_get_prof.return_value = mock_profile
        get_prof_resp = client.get(f"/api/v1/targets/{target_id}/profile")
        assert get_prof_resp.status_code == 200
        assert get_prof_resp.json()["target_id"] == target_id

        # 4. Generate Test Plan
        plan_resp = client.post(f"/api/v1/targets/{target_id}/plan")
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        assert plan_data["target_id"] == target_id
        assert len(plan_data["categories"]) >= 5
        # Since RAG is detected, LLM08 must be scheduled at priority 1
        llm08_plan = next(c for c in plan_data["categories"] if c["category"] == "LLM08")
        assert llm08_plan["status"] == "scheduled"
        assert llm08_plan["priority"] == 1

