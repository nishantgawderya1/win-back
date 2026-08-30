"""The agent's single source of time.

Two problems this solves.

**Timezone.** Stopping rules and retry windows are *merchant-local* concepts —
"no outreach after 10 PM", "retry at 9 AM", "retry on the 1st". Comparing those
against UTC is wrong by the merchant's offset (5.5 hours for IST), so the
cutoff fires at 3:30 AM local instead of 10 PM. Every business-hours decision
goes through `local_now()`; everything persisted goes through `to_db()` as
naive UTC.

**Demonstrability.** A retry legitimately scheduled for 9 AM tomorrow cannot be
shown in a two-minute demo. `advance()` moves a virtual offset forward so the
scheduler sees those retries come due immediately. The offset applies to the
whole agent at once, so cooldowns, cutoffs and retry windows all stay mutually
consistent — it is a clock, not a per-rule cheat.

Naive datetimes crossing this boundary are interpreted as merchant-local, which
is what a human writing `datetime(2026, 8, 27, 23)` in a test or a CSV means.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.config import settings

MERCHANT_TZ = ZoneInfo(settings.merchant_timezone)

# Outreach resumes in the morning. retry_timing uses the same constant for its
# overnight congestion window, so "quiet hours" means one thing agent-wide.
OUTREACH_RESUME_HOUR = 9

_lock = threading.Lock()
_offset = timedelta(0)


# --- Reading time ----------------------------------------------------------
def utc_now() -> datetime:
    """Timezone-aware UTC, including any demo offset."""
    with _lock:
        offset = _offset
    return datetime.now(timezone.utc) + offset


def local_now() -> datetime:
    """Timezone-aware merchant-local time. Use this for every business rule."""
    return utc_now().astimezone(MERCHANT_TZ)


def to_local(dt: datetime) -> datetime:
    """Normalise to merchant-local. A naive value is assumed to be local."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=MERCHANT_TZ)
    return dt.astimezone(MERCHANT_TZ)


def to_utc(dt: datetime) -> datetime:
    """Normalise to aware UTC. A naive value is assumed to be merchant-local."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=MERCHANT_TZ).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


def to_db(dt: datetime | None) -> datetime | None:
    """Naive UTC for storage — SQLAlchemy DateTime columns drop tzinfo anyway,
    so normalise explicitly rather than letting the offset be silently lost."""
    if dt is None:
        return None
    return to_utc(dt).replace(tzinfo=None)


def from_db(dt: datetime | None) -> datetime | None:
    """Re-attach UTC to a value read back out of the database."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def db_now() -> datetime:
    """Default for persisted timestamp columns."""
    return to_db(utc_now())


# --- The demo offset -------------------------------------------------------
def advance(delta: timedelta) -> timedelta:
    """Move the virtual clock forward. Returns the new total offset."""
    global _offset
    with _lock:
        _offset += delta
        return _offset


def reset() -> None:
    global _offset
    with _lock:
        _offset = timedelta(0)


def offset() -> timedelta:
    with _lock:
        return _offset


def status() -> dict:
    off = offset()
    return {
        "utc_now": utc_now().isoformat(),
        "local_now": local_now().isoformat(),
        "timezone": settings.merchant_timezone,
        "offset_seconds": off.total_seconds(),
        "shifted": off != timedelta(0),
    }
