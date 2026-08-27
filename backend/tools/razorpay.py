"""Razorpay API wrappers + error-code mapping.

In test-mode / demo we don't hit the live payment network for retries — the
executor calls these wrappers, which simulate outcomes deterministically so
the batch demo is reproducible. The real API structure and idempotency-key
discipline are preserved so the integration story is honest.
"""
from __future__ import annotations

import hashlib
import hmac

from backend.config import settings
from backend.graph.state import FailureType

RAZORPAY_ERROR_MAP: dict[str, FailureType] = {
    "BAD_REQUEST_PAYMENT_TIMED_OUT": FailureType.UPI_TIMEOUT,
    "SERVER_ERROR_GATEWAY_TIMEOUT": FailureType.UPI_TIMEOUT,
    "BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS": FailureType.CARD_INSUFFICIENT,
    "INSUFFICIENT_FUNDS": FailureType.CARD_INSUFFICIENT,
    "BAD_REQUEST_PAYMENT_CARD_EXPIRED": FailureType.CARD_BANK_BLOCK,
    "BAD_REQUEST_VALIDATION_FAILURE": FailureType.CARD_BANK_BLOCK,
    "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK": FailureType.CARD_BANK_BLOCK,
    "BAD_REQUEST_PAYMENT_FRAUD_DETECTED": FailureType.CARD_BANK_BLOCK,
    "SUBSCRIPTION_CHARGE_FAILED": FailureType.SUBSCRIPTION_FAILED,
}


def classify_error(error_code: str | None) -> FailureType | None:
    if not error_code:
        return None
    return RAZORPAY_ERROR_MAP.get(error_code.strip().upper())


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """HMAC-SHA256 verification of a Razorpay webhook payload."""
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def idempotency_key(payment_id: str, attempt_count: int) -> str:
    return f"{payment_id}-attempt-{attempt_count}"


async def retry_payment(payment_id: str, attempt_count: int, recovery_score: float) -> dict:
    """Simulated retry. Returns {'recovered': bool, 'idempotency_key': str}.

    Deterministic on (payment_id, attempt, recovery_score) so demos reproduce.
    A higher recovery score => higher chance of success.
    """
    key = idempotency_key(payment_id, attempt_count)
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % 100
    threshold = int(recovery_score * 100)
    return {"recovered": seed < threshold, "idempotency_key": key}


async def create_payment_link(payment_id: str, amount: float) -> str:
    """Simulated payment-link creation. Returns a shareable URL."""
    short = hashlib.sha256(payment_id.encode()).hexdigest()[:10]
    return f"https://rzp.io/i/{short}"
