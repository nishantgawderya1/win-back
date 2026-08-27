"""Single broadcast hub for the live feed.

Every agent action goes through tools/audit.log_action(), which persists to
the DB and calls manager.broadcast(). The frontend LiveFeed subscribes to
/ws/feed and renders each event as a card in real time.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Fan out one JSON event to all connected clients. Never raises."""
        async with self._lock:
            targets = list(self._connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)


# Module-level singleton shared across the app.
manager = ConnectionManager()
