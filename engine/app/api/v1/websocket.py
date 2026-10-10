"""Live Telemetry WebSocket Feed."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.events import event_bus

router = APIRouter()

@router.websocket("/ws/telemetry/{scan_id}")
async def telemetry_websocket(websocket: WebSocket, scan_id: str):
    await websocket.accept()
    queue = event_bus.subscribe(scan_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        event_bus.unsubscribe(scan_id, queue)
