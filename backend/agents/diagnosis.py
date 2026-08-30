"""Node 2 — Diagnosis. The ONLY node that calls an LLM (NVIDIA Nemotron).

Sends failure context to Nemotron and gets back root_cause, confidence,
customer_recovery_score, and a reasoning chain. If the LLM call fails, falls
back to deterministic rule-based classification, scored by how much that
fallback deserves to be trusted, so the pipeline never dies on an API hiccup.
"""
from __future__ import annotations

from backend.graph.state import FailureType, WinBackState
from backend.tools import clock
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


def _fallback_confidence(state: WinBackState) -> float:
    """How much the deterministic fallback should be trusted.

    A single flat penalty for "the LLM was unavailable" conflates two very
    different situations. Mapping BAD_REQUEST_PAYMENT_CARD_EXPIRED to a bank
    block is a lookup, not a guess — it is arguably more reliable than a model
    paraphrasing it. Inferring an abandoned checkout from the *absence* of an
    error code genuinely is a guess.

    Scoring them apart matters because the planner gates automated retries on
    this number (planner.MIN_CONFIDENCE_FOR_RETRY): one flat 0.4 would have
    blocked every retry the moment the model went away, which is not what
    "degrade gracefully" should mean.
    """
    if state.failure_type is None:
        return 0.3  # unrecognised code — the agent does not know what happened
    if state.razorpay_error_code:
        return 0.7  # deterministic error-code mapping
    return 0.45  # inferred from context (no error code at all)


async def diagnosis_node(state: WinBackState) -> WinBackState:
    await log_action(state, "diagnosis", "diagnose_root_cause", "Calling Nemotron for root-cause reasoning.")

    # Local hour: the model reasons about night-time congestion and salary
    # cycles, both of which are meaningless in UTC.
    hour = clock.to_local(state.failed_at).hour if state.failed_at else clock.local_now().hour
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
        confidence = _fallback_confidence(state)
        reasoning = [
            f"Nemotron unavailable ({type(exc).__name__}); used rule-based fallback "
            f"at confidence {confidence:.2f}."
        ]
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
