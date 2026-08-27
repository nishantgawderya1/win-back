"""WinBackState — the single shared data contract.

Every agent node receives a WinBackState and returns an updated COPY via
state.model_copy(update={...}). State is never mutated in place.
Adding a field is safe. Removing one breaks downstream nodes.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FailureType(str, Enum):
    UPI_TIMEOUT = "upi_timeout"                  # BAD_REQUEST_PAYMENT_TIMED_OUT
    CARD_INSUFFICIENT = "card_insufficient"      # INSUFFICIENT_FUNDS
    CARD_BANK_BLOCK = "card_bank_block"          # expired / declined / fraud
    CHECKOUT_ABANDONED = "checkout_abandoned"    # session drop mid-flow
    SUBSCRIPTION_FAILED = "subscription_failed"  # mandate charge failure
    INVOICE_OVERDUE = "invoice_overdue"          # 30/60/90 day B2B


class InterventionType(str, Enum):
    RETRY_PAYMENT = "retry_payment"
    SEND_PAYMENT_LINK = "send_payment_link"
    WHATSAPP_NUDGE = "whatsapp_nudge"
    SMS_HINGLISH = "sms_hinglish"
    EMAIL_RECOVERY = "email_recovery"
    ESCALATE_HUMAN = "escalate_human"
    HALT = "halt"


class AuditEntry(BaseModel):
    agent: str
    action: str
    reason: str
    outcome: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WinBackState(BaseModel):
    # --- Core identity ---
    payment_id: str
    batch_id: str
    amount: float
    currency: str = "INR"
    customer_id: str
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None

    # --- Customer history (fetched by detection) ---
    prior_payments: int = 0
    prior_recoveries: int = 0

    # --- Detection outputs ---
    failure_type: FailureType | None = None
    urgency: str | None = None                    # "high" / "medium" / "low"
    razorpay_error_code: str | None = None
    failed_at: datetime | None = None

    # --- Diagnosis outputs (from Nemotron) ---
    root_cause: str | None = None
    confidence: float | None = None
    customer_recovery_score: float | None = None  # 0.0 to 1.0
    agent_reasoning: list[str] = Field(default_factory=list)

    # --- Planning outputs ---
    intervention: InterventionType | None = None
    retry_scheduled_at: datetime | None = None

    # --- Execution state ---
    attempt_count: int = 0
    last_attempted_at: datetime | None = None
    customer_opted_out: bool = False

    # --- Outcomes ---
    halted: bool = False
    halt_reason: str | None = None
    escalated: bool = False
    escalation_reason: str | None = None
    recovered: bool = False
    recovered_amount: float | None = None

    # --- Promise to pay ---
    promise_to_pay_date: datetime | None = None
    promise_fulfilled: bool | None = None

    # --- Audit ---
    audit_log: list[AuditEntry] = Field(default_factory=list)
