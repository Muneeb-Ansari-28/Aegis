import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def authenticated_client():
    """Test client using the trusted-origin cookie bootstrap used by the UI."""
    from app.api.v1.router import app

    client = TestClient(app, base_url="http://localhost")
    response = client.post(
        "/api/v1/security/bootstrap",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 204
    return client
@pytest.fixture
def sample_canary():
    return "AEGIS-CANARY-7731"
