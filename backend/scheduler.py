"""Retry scheduler — the loop that makes the retry ladder real.

The planner schedules a retry for a window that is deliberately far away: 9 AM
tomorrow for a UPI timeout, the 1st of next month for insufficient funds. The
batch run cannot honour those without violating its own cooldown, so it defers
and moves on. Nothing then picked the payment back up, which is why every
payment stopped at attempt 1 and `max_retry_attempts` was enforced but never
exercised.

This worker closes that loop. It wakes on an interval, asks the database which
payments have a retry window that has now arrived, and re-enters the graph at
the planner for each one. The stopping rules run again on the way through, so a
resumed payment is subject to exactly the same guardrails as a fresh one — the
scheduler decides *when* to reconsider a payment, never *whether* to act.

Because it reads the clock through tools/clock, advancing the demo clock makes
tomorrow's retries due immediately (see backend/api/routes/demo.py).
"""
from __future__ import annotations

import asyncio

from backend.config import settings
from backend.config_runtime import runtime_rules
from backend.db import repository
from backend.db.models import PaymentRecord
from backend.db.session import async_session_factory
from backend.graph.graph import resume_graph
from backend.graph.state import FailureType, WinBackState
from backend.runner import refresh_batch_totals
from backend.tools import clock


def state_from_record(record: PaymentRecord) -> WinBackState:
    """Rebuild the agent's working state from what was persisted.

    Detection and diagnosis outputs are carried across rather than recomputed:
    the failure type and root cause of a payment do not change while it waits
    for its retry window, and re-diagnosing would burn an LLM call per attempt.
    """
    return WinBackState(
        payment_id=record.id,
        batch_id=record.batch_id,
        amount=record.amount,
        customer_id=record.customer_id or "cust_unknown",
        customer_name=record.customer_name,
        customer_phone=record.customer_phone,
        customer_email=record.customer_email,
        customer_opted_out=record.customer_opted_out,
        razorpay_error_code=record.razorpay_error_code,
        prior_payments=record.prior_payments,
        prior_recoveries=record.prior_recoveries,
        failure_type=FailureType(record.failure_type) if record.failure_type else None,
        urgency=record.urgency,
        root_cause=record.root_cause,
        confidence=record.confidence,
        customer_recovery_score=record.customer_recovery_score,
        agent_reasoning=list(record.agent_reasoning or []),
        attempt_count=record.attempt_count,
        last_attempted_at=clock.from_db(record.last_attempted_at),
        retry_scheduled_at=clock.from_db(record.retry_scheduled_at),
        promise_to_pay_date=clock.from_db(record.promise_to_pay_date),
    )


async def run_due_retries(limit: int | None = None) -> dict:
    """Process every payment whose retry window has arrived. Returns a summary."""
    limit = limit or settings.scheduler_batch_limit
    async with async_session_factory() as db:
        due = await repository.list_due_retries(
            db,
            now=clock.to_db(clock.utc_now()),
            max_attempts=runtime_rules.max_retry_attempts,
            limit=limit,
        )
        states = [state_from_record(r) for r in due]

    processed, recovered, still_open = 0, 0, 0
    touched_batches: set[str] = set()
    for state in states:
        try:
            result = WinBackState.model_validate(await resume_graph.ainvoke(state))
        except Exception as exc:  # noqa: BLE001 — one bad record must not stop the queue
            print(f"[scheduler] {state.payment_id} failed: {exc!r}")
            # Drop it from the queue so a permanently broken record cannot spin.
            async with async_session_factory() as db:
                await repository.clear_retry_schedule(db, state.payment_id)
            continue

        processed += 1
        touched_batches.add(result.batch_id)
        if result.recovered:
            recovered += 1
        elif not (result.halted or result.escalated) and result.retry_scheduled_at:
            still_open += 1
        else:
            # Terminal, or the planner declined to schedule anything further —
            # either way it must not remain in the queue.
            async with async_session_factory() as db:
                await repository.clear_retry_schedule(db, result.payment_id)
        await asyncio.sleep(0)  # let WS broadcasts flush between payments

    # A batch's totals were finalised when its run ended, but recoveries keep
    # arriving afterwards through this queue. Recompute so the dashboard does
    # not under-report money the agent actually brought back.
    for batch_id in touched_batches:
        if batch_id != "webhook":
            await refresh_batch_totals(batch_id)

    if processed:
        print(
            f"[scheduler] processed {processed} due retries "
            f"({recovered} recovered, {still_open} rescheduled)"
        )
    return {"processed": processed, "recovered": recovered, "rescheduled": still_open}


async def scheduler_loop() -> None:
    """Background task: poll for due retries until cancelled."""
    interval = settings.scheduler_interval_seconds
    print(f"[scheduler] started — polling every {interval}s")
    try:
        while True:
            try:
                await run_due_retries()
            except Exception as exc:  # noqa: BLE001 — never let the loop die
                print(f"[scheduler] tick failed: {exc!r}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("[scheduler] stopped")
        raise
