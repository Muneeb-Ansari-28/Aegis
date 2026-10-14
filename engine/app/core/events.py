"""In-Process Event Bus feeding WebSocket Telemetry."""
import asyncio
from typing import Dict, List

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        self._history: Dict[str, List[dict]] = {}

    def subscribe(self, channel: str) -> asyncio.Queue:
        if channel not in self._listeners:
            self._listeners[channel] = []
        q = asyncio.Queue()
        for message in self._history.get(channel, []):
            q.put_nowait(message)
        self._listeners[channel].append(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        if channel in self._listeners and q in self._listeners[channel]:
            self._listeners[channel].remove(q)

    async def publish(self, channel: str, message: dict) -> None:
        history = self._history.setdefault(channel, [])
        history.append(message)
        if len(history) > 500:
            del history[:-500]
        if channel in self._listeners:
            for q in self._listeners[channel]:
                await q.put(message)

event_bus = EventBus()
