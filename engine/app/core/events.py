"""In-Process Event Bus feeding WebSocket Telemetry."""
import asyncio
from typing import Dict, List

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, channel: str) -> asyncio.Queue:
        if channel not in self._listeners:
            self._listeners[channel] = []
        q = asyncio.Queue()
        self._listeners[channel].append(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        if channel in self._listeners and q in self._listeners[channel]:
            self._listeners[channel].remove(q)

    async def publish(self, channel: str, message: dict) -> None:
        if channel in self._listeners:
            for q in self._listeners[channel]:
                await q.put(message)

event_bus = EventBus()
