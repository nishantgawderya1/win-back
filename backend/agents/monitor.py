"""Node 5 — Monitor. Checks outcome and decides loop-back vs. report.

The routing itself lives in graph.py (route_from_monitor); this node records
the observed outcome and any promise-to-pay follow-up trigger.
"""
from __future__ import annotations

from datetime import datetime

from backend.graph.state import WinBackState
from backend.tools.audit import log_action


async def monitor_node(state: WinBackState) -> WinBackState:
    await log_action(state, "monitor", "check_outcome", "Checking payment status after intervention.")

    if state.recovered:
        outcome = "recovered"
        reason = f"Payment recovered — INR {state.recovered_amount:.0f}."
    elif state.promise_to_pay_date and state.promise_to_pay_date.date() <= datetime.utcnow().date():
        outcome = "promise_due"
        reason = "Promise-to-pay date reached; follow-up triggered."
    else:
        outcome = "not_recovered"
        reason = (
            f"Not recovered yet (attempt {state.attempt_count}). "
            "Routing back to planner if retries remain."
        )

    await log_action(state, "monitor", "check_outcome", reason, outcome=outcome)
    return state
