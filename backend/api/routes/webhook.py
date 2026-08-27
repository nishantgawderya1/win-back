"""Razorpay webhook route (production-grade path).

Signature is verified before any processing. A duplicate-event cache rejects
replays via event_id. The demo uses batch mode; this endpoint exists and is
real for the integration story.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from backend.graph.state import WinBackState
from backend.runner import run_one
from backend.tools.razorpay import verify_webhook_signature

router = APIRouter(prefix="/webhook", tags=["webhook"])

# In-memory idempotency cache (swap for Redis in prod).
_seen_events: set[str] = set()


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    background: BackgroundTasks,
    x_razorpay_signature: str = Header(default=""),
    x_razorpay_event_id: str = Header(default=""),
) -> dict:
    body = await request.body()

    if not verify_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(400, "Invalid webhook signature.")

    if x_razorpay_event_id and x_razorpay_event_id in _seen_events:
        return {"status": "duplicate_ignored"}
    if x_razorpay_event_id:
        _seen_events.add(x_razorpay_event_id)

    payload = await request.json()
    entity = (
        payload.get("payload", {}).get("payment", {}).get("entity", {})
    )

    state = WinBackState(
        payment_id=entity.get("id") or f"pay_{uuid.uuid4().hex[:10]}",
        batch_id="webhook",
        amount=(entity.get("amount", 0) or 0) / 100.0,  # Razorpay amounts are in paise
        customer_id=entity.get("customer_id") or "cust_webhook",
        customer_email=entity.get("email"),
        customer_phone=entity.get("contact"),
        razorpay_error_code=entity.get("error_code") or entity.get("error_reason"),
    )
    background.add_task(run_one, state)
    return {"status": "accepted"}
