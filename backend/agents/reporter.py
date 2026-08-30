"""Node 6 — Reporter. Persists the final PaymentRecord for this payment.

Batch-level aggregation (totals, recovery rate, exception list) is computed by
the runner after all payments finish — see backend/runner.py and
backend/api/routes/reports.py. This node writes the terminal state of one
payment so those aggregations have data to read.
"""
from __future__ import annotations

from backend.config_runtime import runtime_rules
from backend.db.repository import upsert_payment_record
from backend.db.session import async_session_factory
from backend.graph.state import WinBackState
from backend.tools.audit import log_action


async def reporter_node(state: WinBackState) -> WinBackState:
    await log_action(state, "reporter", "persist_record", "Writing final payment record.")

    # retry_scheduled_at is the scheduler's work queue. A payment that is
    # recovered, halted, escalated or out of attempts is owed nothing further,
    # so clear it rather than leaving a window that will never be acted on.
    exhausted = state.attempt_count >= runtime_rules.max_retry_attempts
    if state.recovered or state.halted or state.escalated or exhausted:
        state = state.model_copy(update={"retry_scheduled_at": None})

    async with async_session_factory() as db:
        await upsert_payment_record(db, state)

    status = (
        "recovered" if state.recovered
        else "halted" if state.halted
        else "escalated" if state.escalated
        else "unresolved"
    )
    await log_action(state, "reporter", "persist_record", f"Final status: {status}.", outcome=status)
    return state
