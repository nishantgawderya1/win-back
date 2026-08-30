"""FastAPI app: lifespan (DB init), CORS, WebSocket feed, route mounting."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import (
    batch,
    demo,
    reports,
    settings as settings_routes,
    webhook,
)
from backend.api.auth import current_user, decode_token
from backend.api.ws_manager import manager
from backend.config import settings
from backend.config_runtime import runtime_rules
from backend.db import repository
from backend.scheduler import scheduler_loop
from backend.tools.llm import check_model_available
from backend.db.session import async_session_factory, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Stopping rules default to .env, but a merchant may have edited them in
    # Settings. Load the saved row so the planner enforces their values, not
    # the defaults, from the first payment after boot.
    async with async_session_factory() as db:
        saved = await repository.get_rule_config(db)
        if saved is not None:
            runtime_rules.apply(
                max_retry_attempts=saved.max_retry_attempts,
                min_cooldown_minutes=saved.min_cooldown_minutes,
                outreach_cutoff_hour=saved.outreach_cutoff_hour,
                high_value_threshold_inr=saved.high_value_threshold_inr,
            )

    # Say plainly whether the diagnosis model is actually reachable. A dead
    # model degrades to the rule-based fallback silently, which once ran a
    # whole batch with zero AI involvement and no visible signal.
    app.state.llm_status = await check_model_available()
    if app.state.llm_status["ok"]:
        print(f"[llm] diagnosis model ready: {settings.nemotron_model}")
    else:
        print(f"[llm] WARNING: {app.state.llm_status['reason']}")
        if app.state.llm_status["alternatives"]:
            print(f"[llm] available instead: {', '.join(app.state.llm_status['alternatives'])}")
        print("[llm] diagnosis will fall back to deterministic rules.")

    if settings.auth_required and settings.auth_configured:
        print(f"[auth] required — verifying Supabase tokens via {settings.supabase_jwks_url}")
    elif settings.auth_required:
        print("[auth] WARNING: AUTH_REQUIRED is set but SUPABASE_URL is missing; requests will fail closed.")
    else:
        print("[auth] OPEN — every API route answers anonymous callers. Set AUTH_REQUIRED=true to enforce.")

    task = None
    if settings.scheduler_enabled:
        task = asyncio.create_task(scheduler_loop())

    yield

    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="WinBack AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo scope; tighten for prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# Everything HTTP lives under /api so the client router can own the bare
# paths the product uses (/batch, /audit, /halted, /settings). Without this the
# dev-server proxy intercepts those document requests and the SPA never renders.
API_PREFIX = "/api"

# The webhook authenticates by HMAC over the body, not a user token, so it is
# mounted without the auth dependency. Everything a person can call goes
# through current_user, which is a no-op while AUTH_REQUIRED is false.
app.include_router(webhook.router, prefix=API_PREFIX)

protected = [Depends(current_user)]
app.include_router(batch.router, prefix=API_PREFIX, dependencies=protected)
app.include_router(reports.router, prefix=API_PREFIX, dependencies=protected)
app.include_router(settings_routes.router, prefix=API_PREFIX, dependencies=protected)
app.include_router(demo.router, prefix=API_PREFIX, dependencies=protected)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/feed")
async def ws_feed(ws: WebSocket, token: str = "") -> None:
    """Live agent feed.

    Guarded by the same token as the REST API. Browsers cannot set headers on a
    WebSocket handshake, so the access token arrives as a query parameter —
    which is why it is verified and then never logged. Leaving this open would
    have made the protected API pointless: it streams the same payment data.
    """
    if settings.auth_required:
        try:
            decode_token(token)
        except Exception:  # noqa: BLE001 — any failure is a refusal
            await ws.close(code=4401)  # 4401: application-level "unauthorized"
            return

    await manager.connect(ws)
    try:
        while True:
            # We only push; keep the socket open by awaiting client pings.
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
