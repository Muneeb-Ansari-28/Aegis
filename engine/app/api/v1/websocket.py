"""Live Telemetry WebSocket Feed."""
from typing import Optional
import secrets
from urllib.parse import urlparse
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from app.core.events import event_bus
from app.core.api_auth import get_api_token, is_loopback_host, is_trusted_origin

router = APIRouter()


def is_allowed_origin(origin: Optional[str]) -> bool:
    """Validate WebSocket origin against the exact Aegis UI allowlist."""
    if not origin:
        return False
    return is_trusted_origin(origin)


@router.websocket("/ws/telemetry/{scan_id}")
@router.websocket("/scans/{scan_id}/live")
async def telemetry_websocket(websocket: WebSocket, scan_id: str):
    origin = websocket.headers.get("origin")
    host = websocket.url.hostname
    authorization = websocket.headers.get("authorization", "")
    bearer = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    cookie = websocket.cookies.get("aegis_session", "")
    expected = get_api_token()
    has_token = secrets.compare_digest(bearer, expected) or secrets.compare_digest(cookie, expected)
    if not is_loopback_host(host) or (origin and not is_allowed_origin(origin)) or not has_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    queue = event_bus.subscribe(scan_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        event_bus.unsubscribe(scan_id, queue)
