"""Node 2 — Diagnosis. The ONLY node that calls an LLM (NVIDIA Nemotron).

Sends failure context to Nemotron and gets back root_cause, confidence,
customer_recovery_score, and a reasoning chain. If the LLM call fails, falls
back to deterministic rule-based classification with a lower confidence score
so the pipeline never dies on an API hiccup.
"""
from __future__ import annotations

from datetime import datetime

from backend.graph.state import FailureType, WinBackState
from backend.tools.audit import log_action
from backend.tools.llm import diagnose_failure

# Rule-based fallback root causes keyed by failure type.
_FALLBACK_ROOT_CAUSE: dict[FailureType, str] = {
    FailureType.UPI_TIMEOUT: "UPI network congestion caused a timeout; retry in a low-traffic window.",
    FailureType.CARD_INSUFFICIENT: "Insufficient funds at time of charge; retry after the salary cycle.",
    FailureType.CARD_BANK_BLOCK: "Bank hard-declined the card; retries are pointless, route to an alternate method.",
    FailureType.CHECKOUT_ABANDONED: "Customer dropped mid-checkout; nudge with a payment link.",
    FailureType.SUBSCRIPTION_FAILED: "Mandate charge failed; trigger a renewal flow.",
    FailureType.INVOICE_OVERDUE: "B2B invoice overdue; begin escalating pressure sequence.",
}


def _fallback_recovery_score(state: WinBackState) -> float:
    if state.prior_payments == 0:
        return 0.5
    return max(0.0, min(1.0, state.prior_recoveries / state.prior_payments))


async def diagnosis_node(state: WinBackState) -> WinBackState:
    await log_action(state, "diagnosis", "diagnose_root_cause", "Calling Nemotron for root-cause reasoning.")

    hour = (state.failed_at or datetime.utcnow()).hour
    try:
        result = await diagnose_failure(
            failure_type=state.failure_type.value if state.failure_type else "unknown",
            error_code=state.razorpay_error_code,
            amount=state.amount,
            hour=hour,
            prior_payments=state.prior_payments,
            prior_recoveries=state.prior_recoveries,
            urgency=state.urgency,
        )
        root_cause = result["root_cause"]
        confidence = result["confidence"]
        recovery_score = result["customer_recovery_score"]
        reasoning = result["reasoning"]
        outcome = "nemotron_ok"
    except Exception as exc:  # noqa: BLE001 — deliberate graceful degradation
        root_cause = _FALLBACK_ROOT_CAUSE.get(
            state.failure_type, "Unclassified failure; applying default recovery path."
        )
        recovery_score = _fallback_recovery_score(state)
        confidence = 0.4  # explicitly lower confidence on fallback
        reasoning = [f"Nemotron unavailable ({type(exc).__name__}); used rule-based fallback."]
        outcome = "fallback_rules"

    reason = f"Root cause: {root_cause} (confidence {confidence:.2f}, recovery score {recovery_score:.2f})."
    await log_action(state, "diagnosis", "diagnose_root_cause", reason, outcome=outcome)

    return state.model_copy(
        update={
            "root_cause": root_cause,
            "confidence": confidence,
            "customer_recovery_score": recovery_score,
            "agent_reasoning": [*state.agent_reasoning, *reasoning],
        }
    )
