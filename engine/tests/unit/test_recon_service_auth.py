import pytest

from app.schemas.recon import ReconRequest
from app.services.recon_service import ReconService


def test_active_recon_request_requires_explicit_authorization():
    with pytest.raises(ValueError, match="Explicit authorization"):
        ReconRequest(run_probes=True, authorized=False)


@pytest.mark.asyncio
async def test_recon_service_rejects_unauthorized_active_probes_before_database_access(monkeypatch):
    def database_must_not_be_opened(*_args, **_kwargs):
        raise AssertionError("database should not be touched before authorization is checked")

    monkeypatch.setattr("app.services.recon_service.SessionLocal", database_must_not_be_opened)

    with pytest.raises(PermissionError, match="Explicit authorization"):
        await ReconService.run_recon("target-1", run_probes=True, authorized=False)
