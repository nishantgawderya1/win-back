"""Razorpay webhook route — signature-verified intake, and the recovery loop.

Two kinds of event arrive here.

`payment.failed` starts the agent: a new failure enters the graph and the
recovery workflow begins.

`payment_link.paid` / `payment.captured` close it. The agent sent a real
Razorpay payment link; when the customer actually pays it, Razorpay calls us
back and the payment is marked recovered against the record the agent was
working on. That correlation is what makes a recovery a fact rather than an
assumption — it is confirmed by the gateway, not inferred by us.

Signature is verified before any processing, and a duplicate-event cache
rejects replays via event_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from backend.db import repository
from backend.db.session import get_db
from backend.graph.state import WinBackState
from backend.runner import run_one
from backend.tools import clock
from backend.tools.audit import log_action
from backend.tools.razorpay import verify_webhook_signature

router = APIRouter(prefix="/webhook", tags=["webhook"])

# In-memory idempotency cache (swap for Redis in prod).
_seen_events: set[str] = set()

RECOVERY_EVENTS = {"payment_link.paid", "payment.captured", "order.paid"}


def _entity(payload: dict, key: str) -> dict:
    return payload.get("payload", {}).get(key, {}).get("entity", {}) or {}


async def _handle_recovery(payload: dict, db: AsyncSession) -> dict:
    """Mark the payment recovered, if we can tie this event to one we chased."""
    link = _entity(payload, "payment_link")
    payment = _entity(payload, "payment")

    # Prefer the notes we set when creating the link; fall back to the link id.
    notes = link.get("notes") or payment.get("notes") or {}
    payment_id = notes.get("winback_payment_id")
    record = None

    if payment_id:
        record = await repository.get_payment_record(db, payment_id)
    if record is None and link.get("id"):
        record = await repository.find_by_payment_link(db, link["id"])
    if record is None:
        return {"status": "ignored", "reason": "no matching WinBack payment"}

    if record.recovered:
        return {"status": "already_recorded", "payment_id": record.id}

    # Razorpay reports paise; fall back to the amount we were chasing.
    paise = payment.get("amount") or link.get("amount") or 0
    amount = (paise / 100.0) if paise else record.amount

    await repository.mark_recovered(db, payment_id=record.id, amount=amount)

    # Put it on the live feed and in the audit trail like any other agent action.
    await log_action(
        WinBackState(
            payment_id=record.id,
            batch_id=record.batch_id,
            amount=record.amount,
            customer_id=record.customer_id or "cust_unknown",
        ),
        "monitor",
        "confirm_recovery",
        f"Razorpay confirmed payment of INR {amount:.0f} via payment link.",
        outcome="recovered",
    )
    return {"status": "recovered", "payment_id": record.id, "amount": amount}


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    background: BackgroundTasks,
    x_razorpay_signature: str = Header(default=""),
    x_razorpay_event_id: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> dict:
    body = await request.body()

    if not verify_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(400, "Invalid webhook signature.")

    if x_razorpay_event_id and x_razorpay_event_id in _seen_events:
        return {"status": "duplicate_ignored"}
    if x_razorpay_event_id:
        _seen_events.add(x_razorpay_event_id)

    payload = await request.json()
    event = payload.get("event", "")

    # --- Money came back: close the loop on a payment the agent was chasing ---
    if event in RECOVERY_EVENTS:
        return await _handle_recovery(payload, db)

    # --- A new failure: start the agent on it ---
    entity = _entity(payload, "payment")
    # Razorpay sends created_at as a Unix timestamp. Detection separates an
    # abandoned checkout from an overdue invoice by age, so this matters.
    created_at = entity.get("created_at")
    failed_at = (
        datetime.fromtimestamp(created_at, tz=timezone.utc)
        if isinstance(created_at, (int, float))
        else clock.utc_now()
    )
    state = WinBackState(
        payment_id=entity.get("id") or f"pay_{uuid.uuid4().hex[:10]}",
        batch_id="webhook",
        amount=(entity.get("amount", 0) or 0) / 100.0,  # Razorpay amounts are in paise
        customer_id=entity.get("customer_id") or "cust_webhook",
        customer_email=entity.get("email"),
        customer_phone=entity.get("contact"),
        razorpay_error_code=entity.get("error_code") or entity.get("error_reason"),
        failed_at=failed_at,
    )
    background.add_task(run_one, state)
    return {"status": "accepted", "event": event or "payment.failed"}
