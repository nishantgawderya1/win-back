"""Node 3 — Intervention Planner. Deterministic, no external API.

Order is non-negotiable:
  1. check_stopping_rules() -> if a rule fires, halt and return early.
  2. check_escalation()     -> if a trigger fires, escalate and return early.
  3. pick intervention based on failure_type + recovery_score.
  4. compute adaptive retry timing.
"""
from __future__ import annotations

from backend.graph.state import FailureType, InterventionType, WinBackState
from backend.tools.audit import log_action
from backend.tools.retry_timing import next_retry_at
from backend.tools.rules import check_escalation, check_stopping_rules


def _pick_intervention(state: WinBackState) -> InterventionType:
    ft = state.failure_type
    score = state.customer_recovery_score or 0.5

    if ft == FailureType.UPI_TIMEOUT:
        return InterventionType.RETRY_PAYMENT if score >= 0.5 else InterventionType.SMS_HINGLISH
    if ft == FailureType.CARD_INSUFFICIENT:
        return InterventionType.RETRY_PAYMENT if score >= 0.4 else InterventionType.SMS_HINGLISH
    if ft == FailureType.CHECKOUT_ABANDONED:
        return InterventionType.SEND_PAYMENT_LINK
    if ft == FailureType.SUBSCRIPTION_FAILED:
        return InterventionType.SEND_PAYMENT_LINK
    if ft == FailureType.INVOICE_OVERDUE:
        return InterventionType.EMAIL_RECOVERY
    return InterventionType.WHATSAPP_NUDGE


async def planner_node(state: WinBackState) -> WinBackState:
    await log_action(state, "planner", "plan_intervention", "Checking stopping rules and escalation before acting.")

    # --- Step 1: stopping rules ---
    halt_reason = check_stopping_rules(state)
    if halt_reason:
        await log_action(state, "planner", "halt", halt_reason, outcome="halted")
        return state.model_copy(
            update={"halted": True, "halt_reason": halt_reason, "intervention": InterventionType.HALT}
        )

    # --- Step 2: escalation ---
    escalation_reason = check_escalation(state)
    if escalation_reason:
        await log_action(state, "planner", "escalate", escalation_reason, outcome="escalated")
        return state.model_copy(
            update={
                "escalated": True,
                "escalation_reason": escalation_reason,
                "intervention": InterventionType.ESCALATE_HUMAN,
            }
        )

    # --- Step 3 + 4: intervention + timing ---
    intervention = _pick_intervention(state)
    retry_at = next_retry_at(state.failure_type)

    reason = f"Selected {intervention.value}"
    if retry_at:
        reason += f"; retry scheduled for {retry_at.isoformat()}"
    await log_action(state, "planner", "plan_intervention", reason, outcome="planned")

    return state.model_copy(update={"intervention": intervention, "retry_scheduled_at": retry_at})
