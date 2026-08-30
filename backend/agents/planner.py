"""Node 3 — Intervention Planner. Deterministic, no external API.

Order is non-negotiable:
  1. check_stopping_rules() -> if a rule fires, halt and return early.
  2. check_escalation()     -> if a trigger fires, escalate and return early.
  3. pick intervention based on failure_type + recovery_score + confidence.
  4. compute adaptive retry timing.
"""
from __future__ import annotations

from backend.graph.state import FailureType, InterventionType, WinBackState
from backend.tools.audit import log_action
from backend.tools.retry_timing import next_retry_at
from backend.tools.rules import check_escalation, check_stopping_rules

# Below this, the diagnosis is not trusted enough to spend a payment-network
# retry on. A retry asks the customer's bank to move money on a hypothesis; an
# outreach nudge just asks the customer. When the agent is unsure, it takes the
# action that cannot fail expensively.
MIN_CONFIDENCE_FOR_RETRY = 0.5


def _pick_intervention(state: WinBackState) -> tuple[InterventionType, str | None]:
    """Choose one action. Returns (intervention, downgrade_note)."""
    ft = state.failure_type
    score = state.customer_recovery_score or 0.5
    confidence = state.confidence if state.confidence is not None else 0.5

    if ft == FailureType.UPI_TIMEOUT:
        chosen = InterventionType.RETRY_PAYMENT if score >= 0.5 else InterventionType.SMS_HINGLISH
    elif ft == FailureType.CARD_INSUFFICIENT:
        chosen = InterventionType.RETRY_PAYMENT if score >= 0.4 else InterventionType.SMS_HINGLISH
    elif ft == FailureType.CHECKOUT_ABANDONED:
        chosen = InterventionType.SEND_PAYMENT_LINK
    elif ft == FailureType.SUBSCRIPTION_FAILED:
        chosen = InterventionType.SEND_PAYMENT_LINK
    elif ft == FailureType.INVOICE_OVERDUE:
        chosen = InterventionType.EMAIL_RECOVERY
    else:
        chosen = InterventionType.WHATSAPP_NUDGE

    # A low-confidence diagnosis never authorises an automated retry.
    if chosen == InterventionType.RETRY_PAYMENT and confidence < MIN_CONFIDENCE_FOR_RETRY:
        return (
            InterventionType.SMS_HINGLISH,
            f"diagnosis confidence {confidence:.2f} < {MIN_CONFIDENCE_FOR_RETRY:.2f}, "
            "downgraded retry to outreach",
        )

    return chosen, None


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
    intervention, downgrade = _pick_intervention(state)
    retry_at = next_retry_at(state.failure_type)

    reason = f"Selected {intervention.value} (attempt {state.attempt_count + 1})"
    if downgrade:
        reason += f"; {downgrade}"
    if retry_at:
        reason += f"; next window {retry_at.isoformat()}"
    await log_action(state, "planner", "plan_intervention", reason, outcome="planned")

    updates: dict = {"intervention": intervention, "retry_scheduled_at": retry_at}
    if downgrade:
        updates["agent_reasoning"] = [*state.agent_reasoning, downgrade]

    return state.model_copy(update=updates)
