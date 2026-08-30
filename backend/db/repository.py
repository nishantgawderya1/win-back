"""All database reads/writes live here. Agent nodes stay DB-free and testable.

The graph passes a WinBackState through nodes; persistence to PaymentRecord
happens via upsert_payment_record() from the runner/reporter, and audit rows
are written by tools/audit.py through log_action().
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.tools import clock
from backend.db.models import (
    AuditLog,
    BatchRun,
    HaltedAction,
    PaymentRecord,
    PromiseToPay,
    StoppingRuleConfig,
)
from backend.graph.state import WinBackState


# --- Batch runs -----------------------------------------------------------
async def create_batch_run(db: AsyncSession, batch_id: str, total_records: int) -> BatchRun:
    run = BatchRun(id=batch_id, total_records=total_records, status="running")
    db.add(run)
    await db.commit()
    return run


async def get_batch_run(db: AsyncSession, batch_id: str) -> BatchRun | None:
    return await db.get(BatchRun, batch_id)


async def list_batch_runs(db: AsyncSession, limit: int = 25) -> list[BatchRun]:
    """Newest batches first — powers the dashboard's recent-batches table."""
    rows = await db.execute(
        select(BatchRun).order_by(BatchRun.created_at.desc()).limit(limit)
    )
    return list(rows.scalars().all())


async def bump_batch_progress(db: AsyncSession, batch_id: str) -> None:
    await db.execute(
        update(BatchRun)
        .where(BatchRun.id == batch_id)
        .values(processed=BatchRun.processed + 1)
    )
    await db.commit()


async def finalize_batch(
    db: AsyncSession,
    batch_id: str,
    total_at_risk: float,
    total_recovered: float,
    recovery_rate: float,
) -> None:
    await db.execute(
        update(BatchRun)
        .where(BatchRun.id == batch_id)
        .values(
            total_at_risk=total_at_risk,
            total_recovered=total_recovered,
            recovery_rate=recovery_rate,
            status="complete",
        )
    )
    await db.commit()


# --- Payment records ------------------------------------------------------
async def upsert_payment_record(db: AsyncSession, state: WinBackState) -> None:
    existing = await db.get(PaymentRecord, state.payment_id)
    values = dict(
        batch_id=state.batch_id,
        amount=state.amount,
        customer_id=state.customer_id,
        customer_name=state.customer_name,
        customer_phone=state.customer_phone,
        customer_email=state.customer_email,
        customer_opted_out=state.customer_opted_out,
        razorpay_error_code=state.razorpay_error_code,
        prior_payments=state.prior_payments,
        prior_recoveries=state.prior_recoveries,
        failure_type=state.failure_type.value if state.failure_type else None,
        urgency=state.urgency,
        root_cause=state.root_cause,
        intervention=state.intervention.value if state.intervention else None,
        confidence=state.confidence,
        customer_recovery_score=state.customer_recovery_score,
        payment_link_id=state.payment_link_id,
        payment_link_url=state.payment_link_url,
        attempt_count=state.attempt_count,
        last_attempted_at=clock.to_db(state.last_attempted_at),
        retry_scheduled_at=clock.to_db(state.retry_scheduled_at),
        promise_to_pay_date=clock.to_db(state.promise_to_pay_date),
        recovered=state.recovered,
        recovered_amount=state.recovered_amount,
        halted=state.halted,
        halt_reason=state.halt_reason,
        escalated=state.escalated,
        escalation_reason=state.escalation_reason,
        agent_reasoning=state.agent_reasoning,
    )
    if existing is None:
        db.add(PaymentRecord(id=state.payment_id, **values))
    else:
        for k, v in values.items():
            setattr(existing, k, v)
    await db.commit()


async def list_payment_records(db: AsyncSession, batch_id: str) -> list[PaymentRecord]:
    rows = await db.execute(
        select(PaymentRecord).where(PaymentRecord.batch_id == batch_id)
    )
    return list(rows.scalars().all())


# --- Audit ----------------------------------------------------------------
async def add_audit_log(
    db: AsyncSession,
    *,
    payment_id: str,
    batch_id: str,
    agent: str,
    action: str,
    reason: str,
    outcome: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        payment_id=payment_id,
        batch_id=batch_id,
        agent=agent,
        action=action,
        reason=reason,
        outcome=outcome,
    )
    db.add(entry)
    await db.commit()
    return entry


async def get_audit_trail(db: AsyncSession, payment_id: str) -> list[AuditLog]:
    rows = await db.execute(
        select(AuditLog)
        .where(AuditLog.payment_id == payment_id)
        .order_by(AuditLog.timestamp)
    )
    return list(rows.scalars().all())


async def get_batch_audit(db: AsyncSession, batch_id: str) -> list[AuditLog]:
    rows = await db.execute(
        select(AuditLog)
        .where(AuditLog.batch_id == batch_id)
        .order_by(AuditLog.timestamp)
    )
    return list(rows.scalars().all())


# --- Halted actions -------------------------------------------------------
async def add_halted_action(
    db: AsyncSession, *, payment_id: str, batch_id: str, action: str, halt_reason: str
) -> None:
    db.add(
        HaltedAction(
            payment_id=payment_id,
            batch_id=batch_id,
            action=action,
            halt_reason=halt_reason,
        )
    )
    await db.commit()


async def list_halted_actions(db: AsyncSession, batch_id: str) -> list[HaltedAction]:
    rows = await db.execute(
        select(HaltedAction).where(HaltedAction.batch_id == batch_id)
    )
    return list(rows.scalars().all())


# --- Promise to pay -------------------------------------------------------
async def add_promise(
    db: AsyncSession, *, payment_id: str, customer_id: str, amount: float, promised_date: datetime
) -> None:
    db.add(
        PromiseToPay(
            payment_id=payment_id,
            customer_id=customer_id,
            amount=amount,
            promised_date=promised_date,
        )
    )
    await db.commit()


async def list_pending_promises(db: AsyncSession) -> list[PromiseToPay]:
    """Promises whose date has arrived and that nobody has settled yet.

    "Today" comes from the agent's clock, not the wall clock, so a
    fast-forwarded demo surfaces the promises it has actually reached.
    """
    today = clock.to_db(clock.local_now().replace(hour=23, minute=59, second=59))
    rows = await db.execute(
        select(PromiseToPay).where(
            PromiseToPay.promised_date <= today,
            PromiseToPay.fulfilled.is_(None),
        )
    )
    return list(rows.scalars().all())


# --- Cross-batch queries (global product screens) -------------------------
async def get_payment_record(db: AsyncSession, payment_id: str) -> PaymentRecord | None:
    return await db.get(PaymentRecord, payment_id)


async def query_audit_logs(
    db: AsyncSession,
    *,
    batch_id: str | None = None,
    payment_id: str | None = None,
    agent: str | None = None,
    outcome: str | None = None,
    since: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[AuditLog]:
    """Filtered audit query for the global Audit Trail screen.

    Newest first — the screen is a live-tailing log, not a chronological report.
    (get_audit_trail() stays ascending; a single payment's drill-down reads as
    a story from detection to outcome.)
    """
    stmt = select(AuditLog)
    if batch_id:
        stmt = stmt.where(AuditLog.batch_id == batch_id)
    if payment_id:
        stmt = stmt.where(AuditLog.payment_id == payment_id)
    if agent:
        stmt = stmt.where(AuditLog.agent == agent)
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if since:
        stmt = stmt.where(AuditLog.timestamp >= since)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def query_halted_actions(
    db: AsyncSession, *, batch_id: str | None = None, limit: int = 200
) -> list[tuple[HaltedAction, float | None]]:
    """Halted actions paired with the amount that was consequently not pursued.

    Outer-joined so a halt still surfaces even if the payment record was never
    written (a halt can fire before the reporter runs).
    """
    stmt = select(HaltedAction, PaymentRecord.amount).outerjoin(
        PaymentRecord, PaymentRecord.id == HaltedAction.payment_id
    )
    if batch_id:
        stmt = stmt.where(HaltedAction.batch_id == batch_id)
    stmt = stmt.order_by(HaltedAction.timestamp.desc()).limit(limit)
    rows = await db.execute(stmt)
    return [(h, amount) for h, amount in rows.all()]


async def list_unresolved_records(
    db: AsyncSession, *, batch_id: str | None = None, limit: int = 500
) -> list[PaymentRecord]:
    """Every payment that was not recovered, across batches unless filtered."""
    stmt = select(PaymentRecord).where(PaymentRecord.recovered.is_(False))
    if batch_id:
        stmt = stmt.where(PaymentRecord.batch_id == batch_id)
    stmt = stmt.order_by(PaymentRecord.updated_at.desc()).limit(limit)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


# --- Stopping-rule config -------------------------------------------------
async def get_rule_config(db: AsyncSession) -> StoppingRuleConfig | None:
    """The single saved row, or None when the merchant has never saved."""
    return await db.get(StoppingRuleConfig, 1)


async def save_rule_config(
    db: AsyncSession,
    *,
    max_retry_attempts: int,
    min_cooldown_minutes: int,
    outreach_cutoff_hour: int,
    high_value_threshold_inr: float,
) -> StoppingRuleConfig:
    values = dict(
        max_retry_attempts=max_retry_attempts,
        min_cooldown_minutes=min_cooldown_minutes,
        outreach_cutoff_hour=outreach_cutoff_hour,
        high_value_threshold_inr=high_value_threshold_inr,
    )
    existing = await db.get(StoppingRuleConfig, 1)
    if existing is None:
        existing = StoppingRuleConfig(id=1, **values)
        db.add(existing)
    else:
        for k, v in values.items():
            setattr(existing, k, v)
    await db.commit()
    return existing


# --- Retry scheduler queue ------------------------------------------------
async def list_due_retries(
    db: AsyncSession, *, now: datetime, max_attempts: int, limit: int = 50
) -> list[PaymentRecord]:
    """Payments the agent still owes another attempt, whose window has arrived.

    `now` must be naive UTC (clock.to_db) to match how the column is stored.
    A payment qualifies only while it is genuinely open: recovered, halted and
    escalated records are terminal and must never be picked up again.
    """
    rows = await db.execute(
        select(PaymentRecord)
        .where(
            PaymentRecord.retry_scheduled_at.is_not(None),
            PaymentRecord.retry_scheduled_at <= now,
            PaymentRecord.recovered.is_(False),
            PaymentRecord.halted.is_(False),
            PaymentRecord.escalated.is_(False),
            PaymentRecord.attempt_count < max_attempts,
        )
        .order_by(PaymentRecord.retry_scheduled_at)
        .limit(limit)
    )
    return list(rows.scalars().all())


async def clear_retry_schedule(db: AsyncSession, payment_id: str) -> None:
    """Drop a payment out of the queue without marking it terminal.

    Used when the planner declines to act again (a stopping rule fired, or the
    ceiling is reached) so the scheduler cannot spin on the same record.
    """
    await db.execute(
        update(PaymentRecord)
        .where(PaymentRecord.id == payment_id)
        .values(retry_scheduled_at=None)
    )
    await db.commit()


async def find_by_payment_link(db: AsyncSession, link_id: str) -> PaymentRecord | None:
    """Correlate an inbound Razorpay webhook back to the payment we were chasing."""
    rows = await db.execute(
        select(PaymentRecord).where(PaymentRecord.payment_link_id == link_id).limit(1)
    )
    return rows.scalars().first()


async def mark_recovered(
    db: AsyncSession, *, payment_id: str, amount: float
) -> PaymentRecord | None:
    """Record a confirmed recovery and take the payment out of the retry queue.

    Idempotent: a webhook that arrives twice, or after the agent already
    recorded the recovery, must not double-count the money.
    """
    record = await db.get(PaymentRecord, payment_id)
    if record is None or record.recovered:
        return record
    record.recovered = True
    record.recovered_amount = amount
    record.retry_scheduled_at = None
    await db.commit()
    return record
