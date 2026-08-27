"""Terminal branch nodes: halt and escalate.

The planner sets state.halted / state.escalated and the graph routes here.
These nodes record the terminal reason (HaltedAction table for halts) and then
route to the reporter.
"""
from __future__ import annotations

from backend.db.repository import add_halted_action
from backend.db.session import async_session_factory
from backend.graph.state import WinBackState
from backend.tools.audit import log_action


async def halt_node(state: WinBackState) -> WinBackState:
    reason = state.halt_reason or "Halted by stopping rule."
    await log_action(state, "halt", "halt_action", reason, outcome="halted")

    async with async_session_factory() as db:
        await add_halted_action(
            db,
            payment_id=state.payment_id,
            batch_id=state.batch_id,
            action=state.intervention.value if state.intervention else "unknown",
            halt_reason=reason,
        )
    return state


async def escalate_node(state: WinBackState) -> WinBackState:
    reason = state.escalation_reason or "Escalated to human review."
    await log_action(state, "escalate", "escalate_human", reason, outcome="escalated")
    return state
