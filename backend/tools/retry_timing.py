"""Adaptive retry sequencer — timing is computed per failure type, not fixed.

- UPI timeout late at night  -> retry next morning 09:00 (congestion window).
- Card insufficient funds     -> retry on the 1st (salary-cycle awareness).
- Card bank block             -> no retry (handled by escalation, returns None).
- Everything else             -> retry after the cooldown window.

All windows are merchant-local: "9 AM" means 9 AM where the customer is, not
09:00 UTC. Returned values are timezone-aware local times; persist them with
clock.to_db().
"""
from __future__ import annotations

from datetime import datetime, timedelta

from backend.config_runtime import runtime_rules
from backend.graph.state import FailureType
from backend.tools import clock

_MORNING_HOUR = clock.OUTREACH_RESUME_HOUR
_CONGESTION_START = 22  # 10 PM local


def next_retry_at(failure_type: FailureType | None, now: datetime | None = None) -> datetime | None:
    now = clock.to_local(now) if now is not None else clock.local_now()

    if failure_type == FailureType.CARD_BANK_BLOCK:
        return None  # no retry — escalate to alternate method

    if failure_type == FailureType.UPI_TIMEOUT:
        # Network congestion window at night -> wait for the morning.
        if now.hour >= _CONGESTION_START or now.hour < _MORNING_HOUR:
            target = now.replace(hour=_MORNING_HOUR, minute=0, second=0, microsecond=0)
            if now.hour >= _CONGESTION_START:
                target += timedelta(days=1)
            return target
        return now + timedelta(minutes=runtime_rules.min_cooldown_minutes)

    if failure_type == FailureType.CARD_INSUFFICIENT:
        # Salary cycle awareness — schedule for the 1st of next month.
        year = now.year + (1 if now.month == 12 else 0)
        month = 1 if now.month == 12 else now.month + 1
        return datetime(year, month, 1, _MORNING_HOUR, 0, 0, tzinfo=now.tzinfo)

    if failure_type == FailureType.INVOICE_OVERDUE:
        # B2B chase cadence: a business inbox is read during business hours, so
        # the next nudge goes out tomorrow morning rather than on a cooldown.
        target = (now + timedelta(days=1)).replace(
            hour=_MORNING_HOUR, minute=0, second=0, microsecond=0
        )
        return target

    # Default: honor the cooldown floor.
    return now + timedelta(minutes=runtime_rules.min_cooldown_minutes)
