"""Stopping rules + escalation checks. Enforced by the planner, not the executor.

Stopping rules run FIRST. If any fires the payment is halted. Escalation runs
AFTER stopping rules. These are non-negotiable — never add a "just this once"
exception.

Every time-of-day decision here is *merchant-local* (see tools/clock.py). A
naive `now` passed by a caller is interpreted as local, which is what a test
writing `datetime(2026, 8, 27, 23)` means by it.
"""
from __future__ import annotations

from datetime import datetime

from backend.config_runtime import runtime_rules
from backend.graph.state import FailureType, WinBackState
from backend.tools import clock


def in_quiet_hours(local: datetime) -> bool:
    """True inside the overnight no-outreach window.

    The cutoff hour alone would only silence 10 PM to midnight and then happily
    resume at 2 AM, so the window closes at the same morning hour that
    retry_timing uses to reopen it.
    """
    hour = local.hour
    return hour >= runtime_rules.outreach_cutoff_hour or hour < clock.OUTREACH_RESUME_HOUR


def check_stopping_rules(state: WinBackState, now: datetime | None = None) -> str | None:
    """Return a halt_reason string if any stopping rule fires, else None."""
    local = clock.to_local(now) if now is not None else clock.local_now()

    if state.customer_opted_out:
        return "Customer replied STOP — all outreach permanently halted."

    if state.attempt_count >= runtime_rules.max_retry_attempts:
        return (
            f"Retry ceiling reached ({state.attempt_count}/"
            f"{runtime_rules.max_retry_attempts})."
        )

    if in_quiet_hours(local):
        return (
            f"Outreach cutoff — local time {local.strftime('%H:%M')} is inside "
            f"quiet hours ({runtime_rules.outreach_cutoff_hour}:00–"
            f"{clock.OUTREACH_RESUME_HOUR}:00)."
        )

    if state.last_attempted_at is not None:
        elapsed_min = (local - clock.to_local(state.last_attempted_at)).total_seconds() / 60.0
        if elapsed_min < runtime_rules.min_cooldown_minutes:
            return (
                f"Cooldown active — only {int(elapsed_min)} min since last "
                f"attempt (< {runtime_rules.min_cooldown_minutes} min)."
            )

    return None


def check_escalation(state: WinBackState) -> str | None:
    """Return an escalation_reason if any escalation trigger fires, else None."""
    if state.amount > runtime_rules.high_value_threshold_inr:
        return (
            f"High-value payment (INR {state.amount:.0f} > "
            f"{runtime_rules.high_value_threshold_inr:.0f}) — needs human approval."
        )

    if state.failure_type == FailureType.CARD_BANK_BLOCK:
        return "Hard bank block — automated retries are pointless. Hand to human."

    if state.attempt_count >= runtime_rules.max_retry_attempts:
        return "Retry limit exhausted — escalating to human review."

    return None
