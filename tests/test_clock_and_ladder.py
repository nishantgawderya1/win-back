"""Timezone correctness, the demo clock, and the retry-ladder guardrails.

These cover the behaviour that was previously either wrong (business hours
compared against UTC) or unreachable (a payment never got a second attempt).
"""
from datetime import datetime, timedelta, timezone

import pytest

from backend.agents.detection import INVOICE_OVERDUE_AGE_DAYS, detection_node
from backend.agents.planner import MIN_CONFIDENCE_FOR_RETRY, _pick_intervention
from backend.config import settings
from backend.graph.state import FailureType, InterventionType, WinBackState
from backend.tools import clock
from backend.tools.retry_timing import next_retry_at
from backend.tools.rules import check_stopping_rules, in_quiet_hours


def _state(**kw) -> WinBackState:
    base = dict(payment_id="pay_1", batch_id="b1", amount=1000.0, customer_id="c1")
    base.update(kw)
    return WinBackState(**base)


@pytest.fixture(autouse=True)
def _reset_clock():
    clock.reset()
    yield
    clock.reset()


# --- Timezone --------------------------------------------------------------
def test_cutoff_uses_merchant_local_not_utc():
    """22:00 IST is 16:30 UTC. The old code read the UTC hour and stayed open."""
    ist_2230 = datetime(2026, 8, 27, 22, 30, tzinfo=clock.MERCHANT_TZ)
    assert check_stopping_rules(_state(), now=ist_2230) is not None
    # Same instant expressed in UTC must reach the identical verdict.
    assert check_stopping_rules(_state(), now=ist_2230.astimezone(timezone.utc)) is not None


def test_midday_utc_is_evening_ist_but_still_open():
    noon_utc = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)  # 17:30 IST
    assert check_stopping_rules(_state(), now=noon_utc) is None


def test_quiet_hours_cover_the_small_hours():
    """A bare `hour >= 22` test would happily send outreach at 3 AM."""
    assert in_quiet_hours(datetime(2026, 8, 27, 3, 0, tzinfo=clock.MERCHANT_TZ))
    assert in_quiet_hours(datetime(2026, 8, 27, 23, 0, tzinfo=clock.MERCHANT_TZ))
    assert not in_quiet_hours(datetime(2026, 8, 27, 12, 0, tzinfo=clock.MERCHANT_TZ))


def test_naive_datetimes_are_read_as_merchant_local():
    """Callers and CSVs writing `datetime(...)` mean local time, not UTC."""
    assert check_stopping_rules(_state(), now=datetime(2026, 8, 27, 23)) is not None
    assert check_stopping_rules(_state(), now=datetime(2026, 8, 27, 12)) is None


def test_retry_windows_are_local():
    late = datetime(2026, 8, 27, 23, 43, tzinfo=clock.MERCHANT_TZ)
    result = next_retry_at(FailureType.UPI_TIMEOUT, now=late)
    assert result.hour == 9 and result.day == 28
    assert result.utcoffset() == timedelta(hours=5, minutes=30)


# --- Demo clock ------------------------------------------------------------
def test_advance_moves_the_whole_agent_forward():
    before = clock.utc_now()
    clock.advance(timedelta(days=2))
    assert (clock.utc_now() - before) >= timedelta(days=2) - timedelta(seconds=5)
    assert clock.status()["shifted"] is True
    clock.reset()
    assert clock.status()["shifted"] is False


def test_advancing_does_not_bypass_stopping_rules():
    """The clock changes when the agent acts, never whether it may."""
    clock.advance(timedelta(days=30))
    opted_out = _state(customer_opted_out=True)
    assert check_stopping_rules(opted_out) is not None
    at_ceiling = _state(attempt_count=settings.max_retry_attempts)
    assert check_stopping_rules(at_ceiling) is not None


# --- Confidence gate -------------------------------------------------------
def test_low_confidence_never_authorises_a_retry():
    low = _state(
        failure_type=FailureType.CARD_INSUFFICIENT,
        customer_recovery_score=0.9,
        confidence=MIN_CONFIDENCE_FOR_RETRY - 0.1,
    )
    intervention, note = _pick_intervention(low)
    assert intervention != InterventionType.RETRY_PAYMENT
    assert note is not None


def test_confident_diagnosis_still_retries():
    high = _state(
        failure_type=FailureType.CARD_INSUFFICIENT,
        customer_recovery_score=0.9,
        confidence=0.8,
    )
    intervention, note = _pick_intervention(high)
    assert intervention == InterventionType.RETRY_PAYMENT
    assert note is None


def test_invoice_overdue_gets_email_not_a_nudge():
    state = _state(failure_type=FailureType.INVOICE_OVERDUE, confidence=0.7)
    intervention, _ = _pick_intervention(state)
    assert intervention == InterventionType.EMAIL_RECOVERY


# --- Detection -------------------------------------------------------------
async def test_old_uncoded_failure_is_an_overdue_invoice():
    """Both arrive with no error code; only age separates them."""
    old = _state(
        failed_at=clock.local_now() - timedelta(days=INVOICE_OVERDUE_AGE_DAYS + 5),
        razorpay_error_code="",
    )
    assert (await detection_node(old)).failure_type == FailureType.INVOICE_OVERDUE


async def test_fresh_uncoded_failure_is_an_abandoned_checkout():
    fresh = _state(failed_at=clock.local_now() - timedelta(hours=2), razorpay_error_code="")
    assert (await detection_node(fresh)).failure_type == FailureType.CHECKOUT_ABANDONED
