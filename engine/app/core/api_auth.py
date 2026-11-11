"""Process-scoped local API authentication and trusted browser-origin checks."""
import ipaddress
import os
import secrets
import threading
from pathlib import Path

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.paths import get_app_data_dir

_TRUSTED_ORIGINS = frozenset({
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
})
_BOOTSTRAP_PATH = "/api/v1/security/bootstrap"
_PUBLIC_PATHS = frozenset({"/api/v1/health", _BOOTSTRAP_PATH})
_TOKEN_FILENAME = "api.token"
_PROCESS_TOKEN = secrets.token_urlsafe(48)
_TOKEN_LOCK = threading.Lock()
_TOKEN_FILE_READY = False


def api_token_path() -> Path:
    return get_app_data_dir() / _TOKEN_FILENAME


def get_api_token() -> str:
    """Return this engine process's token and write it for trusted local CLI use."""
    global _TOKEN_FILE_READY
    if not _TOKEN_FILE_READY:
        with _TOKEN_LOCK:
            if not _TOKEN_FILE_READY:
                path = api_token_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                temporary.write_text(_PROCESS_TOKEN, encoding="utf-8")
                os.replace(temporary, path)
                try:
                    path.chmod(0o600)
                except OSError:
                    # Windows inherits the user's profile ACL; POSIX permissions are tightened above.
                    pass
                _TOKEN_FILE_READY = True
    return _PROCESS_TOKEN


def is_trusted_origin(origin: str | None) -> bool:
    return origin in _TRUSTED_ORIGINS


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip("[]").lower().rstrip(".")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


class LocalAPIAuthMiddleware(BaseHTTPMiddleware):
    """Require the process token on private routes and reject untrusted web origins."""

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        host = request.url.hostname
        if not is_loopback_host(host):
            return JSONResponse({"detail": "Aegis API accepts loopback Host headers only."}, status_code=403)
        if origin and not is_trusted_origin(origin):
            return JSONResponse({"detail": "Untrusted browser origin."}, status_code=403)
        if request.method == "OPTIONS":
            if origin and not is_trusted_origin(origin):
                return JSONResponse({"detail": "Untrusted browser origin."}, status_code=403)
            return await call_next(request)
        if request.url.path == _BOOTSTRAP_PATH:
            if request.method != "POST" or not is_trusted_origin(origin):
                return JSONResponse({"detail": "Session bootstrap requires a trusted Aegis UI origin."}, status_code=403)
            return await call_next(request)
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        bearer = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
        cookie = request.cookies.get("aegis_session", "")
        expected = get_api_token()
        if not (secrets.compare_digest(bearer, expected) or secrets.compare_digest(cookie, expected)):
            return JSONResponse({"detail": "Missing or invalid Aegis API credential."}, status_code=401)
        return await call_next(request)


def set_api_session_cookie(response: Response) -> None:
    response.set_cookie(
        key="aegis_session",
        value=get_api_token(),
        httponly=True,
        secure=False,
        samesite="strict",
        path="/api/v1",
    )
