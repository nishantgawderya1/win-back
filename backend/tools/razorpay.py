"""Razorpay API wrappers + error-code mapping.

Two different things live here, and the difference matters.

**Payment links are real.** `create_payment_link()` calls Razorpay's
`/payment_links` API with the configured test-mode key and returns a genuinely
payable short URL. When the customer pays it, Razorpay fires `payment_link.paid`
at our webhook and the agent records a real recovery.

**Card/UPI retries are simulated.** There is no Razorpay API that re-charges a
failed payment — a failed authorization cannot be replayed, and recovering it
genuinely requires a fresh authorization from the customer, which is what the
payment link is for. `retry_payment()` therefore models the outcome
deterministically rather than pretending to hit the network. That is a property
of how card payments work, not a shortcut.

Every call carries an idempotency key, and both paths degrade to simulation when
no real key is configured so the demo runs without credentials.
"""
from __future__ import annotations

import base64
import hashlib
import hmac

import httpx

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


def has_live_credentials() -> bool:
    """True when a real key is configured rather than the placeholder default."""
    return not (
        settings.razorpay_key_id.endswith("placeholder")
        or settings.razorpay_key_secret.startswith("placeholder")
    )


def _auth_header() -> str:
    raw = f"{settings.razorpay_key_id}:{settings.razorpay_key_secret}".encode()
    return f"Basic {base64.b64encode(raw).decode()}"


async def retry_payment(payment_id: str, attempt_count: int, recovery_score: float) -> dict:
    """Simulated retry. Returns {'recovered': bool, 'idempotency_key': str}.

    Deterministic on (payment_id, attempt, recovery_score) so demos reproduce.
    A higher recovery score => higher chance of success. See the module
    docstring for why a real retry endpoint does not exist to call.
    """
    key = idempotency_key(payment_id, attempt_count)
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % 100
    threshold = int(recovery_score * 100)
    return {"recovered": seed < threshold, "idempotency_key": key}


def _simulated_link(payment_id: str) -> dict:
    short = hashlib.sha256(payment_id.encode()).hexdigest()[:10]
    return {
        "id": None,
        "short_url": f"https://rzp.io/i/{short}",
        "live": False,
        "error": None,
    }


async def create_payment_link(
    payment_id: str,
    amount: float,
    *,
    customer_name: str | None = None,
    customer_email: str | None = None,
    customer_phone: str | None = None,
    attempt: int = 1,
) -> dict:
    """Create a real Razorpay payment link. Returns id, short_url and liveness.

    `notes` carries our payment id back to us: when the link is paid, the
    webhook receives those notes and can correlate the payment to the record
    the agent was working on, which is what turns a sent link into a confirmed
    recovery.

    Falls back to a simulated URL when no credentials are configured, or when
    the API call fails — a failed link must not take the whole batch down.
    """
    if not has_live_credentials():
        return _simulated_link(payment_id)

    body = {
        "amount": int(round(amount * 100)),  # Razorpay works in paise
        "currency": "INR",
        "description": f"Payment recovery for {payment_id}",
        "customer": {
            "name": customer_name or "Customer",
            "email": customer_email or "",
            "contact": customer_phone or "",
        },
        # The agent owns outreach; Razorpay must not also message the customer.
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "notes": {"winback_payment_id": payment_id, "winback_attempt": str(attempt)},
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{settings.razorpay_base_url}/payment_links",
                json=body,
                headers={
                    "Authorization": _auth_header(),
                    "Content-Type": "application/json",
                    # Razorpay dedupes on this, so a retried attempt cannot
                    # create a second link for the same attempt.
                    "X-Payment-Link-Reference-Id": idempotency_key(payment_id, attempt),
                },
            )
        if response.status_code in (200, 201):
            data = response.json()
            return {
                "id": data.get("id"),
                "short_url": data.get("short_url"),
                "live": True,
                "error": None,
            }
        detail = response.json().get("error", {}).get("description", response.text[:120])
        return {**_simulated_link(payment_id), "error": f"{response.status_code}: {detail}"}
    except Exception as exc:  # noqa: BLE001 — outreach must survive a link failure
        return {**_simulated_link(payment_id), "error": f"{type(exc).__name__}"}


async def fetch_payment_link(link_id: str) -> dict | None:
    """Read a link's current state — 'paid' is the real recovery signal."""
    if not has_live_credentials() or not link_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{settings.razorpay_base_url}/payment_links/{link_id}",
                headers={"Authorization": _auth_header()},
            )
        return response.json() if response.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None
