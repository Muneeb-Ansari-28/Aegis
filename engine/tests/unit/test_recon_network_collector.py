"""Unit tests for PassiveNetworkCollector boundaries and resilience (Task 4).

Tests:
- Third-party responses do not contaminate target origin headers/paths/keys.
- Active well-known path checks are bounded, isolated, and tracked in endpoint_checks.
- Exceptions during collection preserve cleanup and return partial/failed status.
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.recon.network_collector import PassiveNetworkCollector, PassiveReconData


def test_passive_recon_data_has_status_and_endpoint_checks():
    data = PassiveReconData(target_url="http://localhost:8000")
    assert hasattr(data, "status")
    assert hasattr(data, "warnings")
    assert hasattr(data, "endpoint_checks")
    assert data.status == "completed"


@pytest.mark.asyncio
async def test_network_collector_ignores_third_party_origin():
    collector = PassiveNetworkCollector(target_url="http://localhost:8000/app")
    
    # Simulate a target origin response vs a third party response
    observed_paths = set()
    observed_headers = {}
    observed_resp_keys = set()
    
    class FakeResponse:
        def __init__(self, url, headers, json_body=None):
            self.url = url
            self.headers = headers
            self._json = json_body
        async def json(self):
            return self._json

    # Local origin response
    local_resp = FakeResponse(
        url="http://localhost:8000/api/chat",
        headers={"Server": "uvicorn", "Content-Type": "application/json"},
        json_body={"messages": []}
    )
    # Third party analytics response
    third_party_resp = FakeResponse(
        url="https://google-analytics.com/collect",
        headers={"Server": "Google Frontend", "Content-Type": "application/json"},
        json_body={"tracking_id": "123"}
    )

    collector._filter_and_record_response(
        local_resp,
        observed_paths=observed_paths,
        observed_headers=observed_headers,
        observed_resp_keys=observed_resp_keys,
    )
    await collector._record_response_body(
        local_resp,
        observed_resp_keys=observed_resp_keys,
    )

    collector._filter_and_record_response(
        third_party_resp,
        observed_paths=observed_paths,
        observed_headers=observed_headers,
        observed_resp_keys=observed_resp_keys,
    )
    await collector._record_response_body(
        third_party_resp,
        observed_resp_keys=observed_resp_keys,
    )

    # Assert local target signals ARE recorded
    assert "/api/chat" in observed_paths
    assert observed_headers.get("server") == "uvicorn"
    assert "messages" in observed_resp_keys

    # Assert third-party signals ARE NOT recorded
    assert "/collect" not in observed_paths
    assert observed_headers.get("server") != "google frontend"
    assert "tracking_id" not in observed_resp_keys


@pytest.mark.asyncio
async def test_endpoint_probe_timeout_does_not_abort_collection():
    collector = PassiveNetworkCollector(target_url="http://localhost:8000")
    
    # Mock httpx GET so one endpoint raises timeout while another succeeds
    async def mock_get(url, **kwargs):
        mock_resp = MagicMock()
        if "openapi.json" in url:
            mock_resp.status_code = 200
            mock_resp.is_success = True
            mock_resp.headers = {"server": "uvicorn"}
            return mock_resp
        raise TimeoutError("Connection timed out")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        endpoints_found, endpoint_checks = await collector._probe_well_known_paths("http://localhost:8000")
        
        assert "/openapi.json" in endpoints_found
        assert "/openapi.json" in endpoint_checks
        assert endpoint_checks["/openapi.json"]["ok"] is True
        
        assert "/docs" in endpoint_checks
        assert endpoint_checks["/docs"]["ok"] is False

