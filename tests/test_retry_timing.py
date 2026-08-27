"""Adaptive retry sequencer tests."""
from datetime import datetime

from backend.graph.state import FailureType
from backend.tools.retry_timing import next_retry_at


def test_bank_block_no_retry():
    assert next_retry_at(FailureType.CARD_BANK_BLOCK) is None


def test_upi_night_reschedules_to_morning():
    late = datetime(2026, 8, 27, 23, 43)
    result = next_retry_at(FailureType.UPI_TIMEOUT, now=late)
    assert result is not None
    assert result.hour == 9
    assert result.day == 28  # next morning


def test_card_insufficient_salary_cycle():
    on_25th = datetime(2026, 8, 25, 14)
    result = next_retry_at(FailureType.CARD_INSUFFICIENT, now=on_25th)
    assert result is not None
    assert result.day == 1
    assert result.month == 9
