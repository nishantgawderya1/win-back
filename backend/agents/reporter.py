"""Node 6 — Reporter. Persists the final PaymentRecord for this payment.

Batch-level aggregation (totals, recovery rate, exception list) is computed by
the runner after all payments finish — see backend/runner.py and
backend/api/routes/reports.py. This node writes the terminal state of one
payment so those aggregations have data to read.
"""
from __future__ import annotations

from backend.db.repository import upsert_payment_record
from backend.db.session import async_session_factory
from backend.graph.state import WinBackState
from backend.tools.audit import log_action


async def reporter_node(state: WinBackState) -> WinBackState:
    await log_action(state, "reporter", "persist_record", "Writing final payment record.")

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
