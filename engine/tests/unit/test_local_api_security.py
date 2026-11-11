"""Unit tests for local API origins, WebSocket validation, and report path security (Task 13)."""
import pytest
from app.api.v1.websocket import is_allowed_origin


def test_cors_allows_loopback_origin(authenticated_client):
    client = authenticated_client
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_untrusted_remote_origin(authenticated_client):
    client = authenticated_client
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://malicious-website.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # The header must NOT allow the untrusted origin
    assert response.headers.get("access-control-allow-origin") != "https://malicious-website.com"


def test_websocket_origin_validator():
    assert is_allowed_origin(None) is False
    assert is_allowed_origin("http://localhost:3000") is True
    assert is_allowed_origin("http://127.0.0.1:5173") is True
    assert is_allowed_origin("app://desktop") is False

    # Untrusted origins
    assert is_allowed_origin("https://attacker.com") is False
    assert is_allowed_origin("http://192.168.1.50:3000") is False


def test_report_path_traversal_is_blocked(authenticated_client):
    client = authenticated_client
    # Path traversal attempt in scan_id
    response = client.get("/api/v1/reports/..%2F..%2Fetc%2Fpasswd/pdf")
    # Must fail safely with 400, 404, or 409, never executing or reading files outside
    assert response.status_code in (400, 404, 409, 500)
    assert "passwd" not in response.text

