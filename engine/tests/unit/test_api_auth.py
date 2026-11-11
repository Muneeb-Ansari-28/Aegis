"""Tests for process-token API authentication and trusted-origin boundaries."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import api_auth


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api_auth, "get_api_token", lambda: "process-secret")
    app = FastAPI()
    app.add_middleware(api_auth.LocalAPIAuthMiddleware)

    @app.get("/api/v1/private")
    async def private_route():
        return {"ok": True}

    @app.post("/api/v1/security/bootstrap")
    async def bootstrap_route():
        return {"ok": True}

    return TestClient(app, base_url="http://localhost")


def test_trusted_origins_are_exact():
    assert api_auth.is_trusted_origin("http://localhost:3000")
    assert api_auth.is_trusted_origin("http://127.0.0.1:5173")
    assert not api_auth.is_trusted_origin("http://localhost:9999")
    assert not api_auth.is_trusted_origin("https://attacker.example")


def test_private_api_rejects_missing_credentials(client):
    response = client.get("/api/v1/private", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 401


def test_private_api_accepts_process_bearer_for_local_cli(client):
    response = client.get(
        "/api/v1/private",
        headers={"Authorization": "Bearer process-secret", "Host": "127.0.0.1:8765"},
    )
    assert response.status_code == 200


def test_private_api_accepts_cookie_only_from_trusted_origin(client):
    response = client.get(
        "/api/v1/private",
        headers={"Origin": "http://localhost:3000", "Host": "localhost:8765"},
        cookies={"aegis_session": "process-secret"},
    )
    assert response.status_code == 200


def test_untrusted_origin_is_rejected_even_with_valid_cookie(client):
    response = client.get(
        "/api/v1/private",
        headers={"Origin": "https://attacker.example", "Host": "localhost:8765"},
        cookies={"aegis_session": "process-secret"},
    )
    assert response.status_code == 403


def test_bootstrap_requires_trusted_origin(client):
    trusted = client.post(
        "/api/v1/security/bootstrap", headers={"Origin": "http://localhost:3000"}
    )
    untrusted = client.post(
        "/api/v1/security/bootstrap", headers={"Origin": "https://attacker.example"}
    )
    assert trusted.status_code == 200
    assert untrusted.status_code == 403
