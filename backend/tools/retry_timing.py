"""Adaptive retry sequencer — timing is computed per failure type, not fixed.

- UPI timeout late at night  -> retry next morning 09:00 (congestion window).
- Card insufficient funds     -> retry on the 1st (salary-cycle awareness).
- Card bank block             -> no retry (handled by escalation, returns None).
- Everything else             -> retry after the cooldown window.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from backend.config import settings
from backend.graph.state import FailureType

_MORNING_HOUR = 9
_CONGESTION_START = 22  # 10 PM


def next_retry_at(failure_type: FailureType | None, now: datetime | None = None) -> datetime | None:
    now = now or datetime.utcnow()

    if failure_type == FailureType.CARD_BANK_BLOCK:
        return None  # no retry — escalate to alternate method

    if failure_type == FailureType.UPI_TIMEOUT:
        # Network congestion window at night -> wait for the morning.
        if now.hour >= _CONGESTION_START or now.hour < _MORNING_HOUR:
            target = now.replace(hour=_MORNING_HOUR, minute=0, second=0, microsecond=0)
            if now.hour >= _CONGESTION_START:
                target += timedelta(days=1)
            return target
        return now + timedelta(minutes=settings.min_cooldown_minutes)

    if failure_type == FailureType.CARD_INSUFFICIENT:
        # Salary cycle awareness — schedule for the 1st of next month.
        year = now.year + (1 if now.month == 12 else 0)
        month = 1 if now.month == 12 else now.month + 1
        return datetime(year, month, 1, _MORNING_HOUR, 0, 0)

    # Default: honor the cooldown floor.
    return now + timedelta(minutes=settings.min_cooldown_minutes)
