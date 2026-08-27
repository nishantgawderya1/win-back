"""Detection classification tests (pure rules, no LLM)."""
from backend.graph.state import FailureType
from backend.tools.razorpay import classify_error


def test_upi_timeout_maps():
    assert classify_error("BAD_REQUEST_PAYMENT_TIMED_OUT") == FailureType.UPI_TIMEOUT


def test_insufficient_funds_maps():
    assert classify_error("INSUFFICIENT_FUNDS") == FailureType.CARD_INSUFFICIENT


def test_bank_block_maps():
    assert classify_error("BAD_REQUEST_PAYMENT_FRAUD_DETECTED") == FailureType.CARD_BANK_BLOCK


def test_case_insensitive():
    assert classify_error("insufficient_funds") == FailureType.CARD_INSUFFICIENT


def test_unknown_returns_none():
    assert classify_error("SOME_UNKNOWN_CODE") is None
    assert classify_error(None) is None
