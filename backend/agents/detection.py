"""Node 1 — Detection. Pure rules, no LLM.

Classifies failure_type from the Razorpay error code and assigns urgency from
amount + elapsed time. Customer contact/history is assumed pre-populated on the
incoming state (from webhook payload or CSV row).
"""
from __future__ import annotations

from datetime import datetime

from backend.graph.state import FailureType, WinBackState
from backend.tools.audit import log_action
from backend.tools.razorpay import classify_error


def _assign_urgency(state: WinBackState, now: datetime) -> str:
    if state.amount > 25000:
        return "high"
    if state.failed_at is not None:
        hours = (now - state.failed_at).total_seconds() / 3600.0
        if hours > 48:
            return "high"
        if hours > 12:
            return "medium"
    if state.amount > 5000:
        return "medium"
    return "low"


async def detection_node(state: WinBackState) -> WinBackState:
    await log_action(state, "detection", "classify_failure", "Classifying failure type from error code.")

    now = datetime.utcnow()
    failure_type = classify_error(state.razorpay_error_code)

    # No error code (e.g. checkout abandonment) -> infer from context.
    if failure_type is None and state.razorpay_error_code in (None, "", "NONE"):
        failure_type = FailureType.CHECKOUT_ABANDONED

    urgency = _assign_urgency(state, now)

    reason = (
        f"Error '{state.razorpay_error_code}' -> {failure_type.value if failure_type else 'unknown'}; "
        f"amount INR {state.amount:.0f}; urgency {urgency}."
    )
    await log_action(state, "detection", "classify_failure", reason, outcome="completed")

    return state.model_copy(update={"failure_type": failure_type, "urgency": urgency})
