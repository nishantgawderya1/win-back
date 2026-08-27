"""FastAPI app: lifespan (DB init), CORS, WebSocket feed, route mounting."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import batch, reports, webhook
from backend.api.ws_manager import manager
from backend.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="WinBack AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo scope; tighten for prod
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(batch.router)
app.include_router(reports.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/feed")
async def ws_feed(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            # We only push; keep the socket open by awaiting client pings.
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
