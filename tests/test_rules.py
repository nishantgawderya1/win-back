"""Stopping-rule + escalation tests. These are the non-negotiable guardrails."""
from datetime import datetime, timedelta

from backend.config import settings
from backend.graph.state import FailureType, WinBackState
from backend.tools.rules import check_escalation, check_stopping_rules


def _state(**kw) -> WinBackState:
    base = dict(payment_id="pay_1", batch_id="b1", amount=1000.0, customer_id="c1")
    base.update(kw)
    return WinBackState(**base)


def test_opt_out_halts():
    s = _state(customer_opted_out=True)
    assert check_stopping_rules(s, now=datetime(2026, 8, 27, 12)) is not None


def test_retry_ceiling_halts():
    s = _state(attempt_count=settings.max_retry_attempts)
    assert check_stopping_rules(s, now=datetime(2026, 8, 27, 12)) is not None


def test_after_cutoff_halts():
    s = _state()
    assert check_stopping_rules(s, now=datetime(2026, 8, 27, 23)) is not None


def test_cooldown_halts():
    now = datetime(2026, 8, 27, 12)
    s = _state(last_attempted_at=now - timedelta(minutes=10))
    assert check_stopping_rules(s, now=now) is not None


def test_clean_state_passes():
    now = datetime(2026, 8, 27, 12)
    s = _state()
    assert check_stopping_rules(s, now=now) is None


def test_high_value_escalates():
    s = _state(amount=settings.high_value_threshold_inr + 1)
    assert check_escalation(s) is not None


def test_bank_block_escalates():
    s = _state(failure_type=FailureType.CARD_BANK_BLOCK)
    assert check_escalation(s) is not None
