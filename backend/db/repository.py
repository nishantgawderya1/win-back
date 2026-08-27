"""All database reads/writes live here. Agent nodes stay DB-free and testable.

The graph passes a WinBackState through nodes; persistence to PaymentRecord
happens via upsert_payment_record() from the runner/reporter, and audit rows
are written by tools/audit.py through log_action().
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    AuditLog,
    BatchRun,
    HaltedAction,
    PaymentRecord,
    PromiseToPay,
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
        failure_type=state.failure_type.value if state.failure_type else None,
        root_cause=state.root_cause,
        intervention=state.intervention.value if state.intervention else None,
        confidence=state.confidence,
        customer_recovery_score=state.customer_recovery_score,
        attempt_count=state.attempt_count,
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
    today = datetime.combine(date.today(), datetime.min.time())
    rows = await db.execute(
        select(PromiseToPay).where(
            PromiseToPay.promised_date <= today,
            PromiseToPay.fulfilled.is_(None),
        )
    )
    return list(rows.scalars().all())
