"""Node 4 — Executor. Runs exactly the one action the planner chose.

- Every Razorpay payment call carries an idempotency key.
- attempt_count is incremented regardless of success or failure.
- Comms tools are mocked but typed. Logs before and after.
- The executor never picks its own action — that is the planner's job.
"""
from __future__ import annotations

from backend.db.repository import add_promise
from backend.db.session import async_session_factory
from backend.graph.state import InterventionType, WinBackState
from backend.tools import clock, comms, razorpay
from backend.tools.audit import log_action

OUTREACH_INTERVENTIONS = (
    InterventionType.SEND_PAYMENT_LINK,
    InterventionType.SMS_HINGLISH,
    InterventionType.WHATSAPP_NUDGE,
    InterventionType.EMAIL_RECOVERY,
)


async def executor_node(state: WinBackState) -> WinBackState:
    intervention = state.intervention
    await log_action(state, "executor", intervention.value if intervention else "noop", "Executing planned intervention.")

    now = clock.utc_now()
    updates: dict = {
        "attempt_count": state.attempt_count + 1,
        "last_attempted_at": now,
    }
    outcome = "attempted"

    if intervention == InterventionType.RETRY_PAYMENT:
        result = await razorpay.retry_payment(
            state.payment_id, state.attempt_count, state.customer_recovery_score or 0.5
        )
        if result["recovered"]:
            updates.update(recovered=True, recovered_amount=state.amount)
            outcome = "recovered"
        else:
            outcome = "retry_failed"
        detail = f"Retry (idempotency {result['idempotency_key']}) -> {outcome}."

    elif intervention in OUTREACH_INTERVENTIONS:
        link = await razorpay.create_payment_link(
            state.payment_id,
            state.amount,
            customer_name=state.customer_name,
            customer_email=state.customer_email,
            customer_phone=state.customer_phone,
            attempt=state.attempt_count + 1,
        )
        updates["payment_link_id"] = link["id"]
        updates["payment_link_url"] = link["short_url"]

        detail = await _send_outreach(state, intervention, link["short_url"])
        detail += (
            f" Razorpay link {link['id']}."
            if link["live"]
            else f" Simulated link ({link['error'] or 'no Razorpay credentials configured'})."
        )
        outcome = "outreach_sent"

        # Outreach can draw a reply. A customer who names a date changes what
        # the agent should do next: chase the promise, not the cooldown.
        promised = comms.simulate_promise_reply(
            state.payment_id, state.attempt_count, state.customer_recovery_score or 0.5
        )
        if promised is not None:
            updates["promise_to_pay_date"] = promised
            async with async_session_factory() as db:
                await add_promise(
                    db,
                    payment_id=state.payment_id,
                    customer_id=state.customer_id,
                    amount=state.amount,
                    promised_date=clock.to_db(promised),
                )
            detail += f" Customer promised to pay by {promised.date().isoformat()}."
            outcome = "promise_received"

    else:
        detail = f"No executable action for intervention {intervention}."
        outcome = "noop"

    await log_action(state, "executor", intervention.value if intervention else "noop", detail, outcome=outcome)
    return state.model_copy(update=updates)


async def _send_outreach(state: WinBackState, intervention: InterventionType, link: str) -> str:
    ft = state.failure_type.value if state.failure_type else "unknown"
    if intervention == InterventionType.SMS_HINGLISH:
        msg = comms.render_hinglish_sms(ft, state.customer_name, state.amount, link)
        await comms.send_sms(state.customer_phone, msg)
        return f"Hinglish SMS sent to {state.customer_phone}."
    if intervention == InterventionType.WHATSAPP_NUDGE:
        await comms.send_whatsapp(state.customer_phone, f"Payment pending: {link}")
        return f"WhatsApp nudge sent to {state.customer_phone}."
    if intervention == InterventionType.EMAIL_RECOVERY:
        await comms.send_email(state.customer_email, "Payment reminder", f"Please pay: {link}")
        return f"Recovery email sent to {state.customer_email}."
    # SEND_PAYMENT_LINK default
    await comms.send_sms(state.customer_phone, f"Complete your payment: {link}")
    return f"Payment link sent to {state.customer_phone}."
