"""Stopping rules + escalation checks. Enforced by the planner, not the executor.

Stopping rules run FIRST. If any fires the payment is halted. Escalation runs
AFTER stopping rules. These are non-negotiable — never add a "just this once"
exception.
"""
from __future__ import annotations

from datetime import datetime

from backend.config import settings
from backend.graph.state import FailureType, WinBackState


def check_stopping_rules(state: WinBackState, now: datetime | None = None) -> str | None:
    """Return a halt_reason string if any stopping rule fires, else None."""
    now = now or datetime.utcnow()

    if state.customer_opted_out:
        return "Customer replied STOP — all outreach permanently halted."

    if state.attempt_count >= settings.max_retry_attempts:
        return (
            f"Retry ceiling reached ({state.attempt_count}/"
            f"{settings.max_retry_attempts})."
        )

    if now.hour >= settings.outreach_cutoff_hour:
        return (
            f"Outreach cutoff — current hour {now.hour}:00 is past "
            f"{settings.outreach_cutoff_hour}:00 (10 PM)."
        )

    if state.last_attempted_at is not None:
        elapsed_min = (now - state.last_attempted_at).total_seconds() / 60.0
        if elapsed_min < settings.min_cooldown_minutes:
            return (
                f"Cooldown active — only {int(elapsed_min)} min since last "
                f"attempt (< {settings.min_cooldown_minutes} min)."
            )

    return None


def check_escalation(state: WinBackState) -> str | None:
    """Return an escalation_reason if any escalation trigger fires, else None."""
    if state.amount > settings.high_value_threshold_inr:
        return (
            f"High-value payment (INR {state.amount:.0f} > "
            f"{settings.high_value_threshold_inr:.0f}) — needs human approval."
        )

    if state.failure_type == FailureType.CARD_BANK_BLOCK:
        return "Hard bank block — automated retries are pointless. Hand to human."

    if state.attempt_count >= settings.max_retry_attempts:
        return "Retry limit exhausted — escalating to human review."

    return None
