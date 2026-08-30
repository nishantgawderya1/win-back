"""Reporting routes: summary, exceptions, audit trail, CSV export, halted, promises."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import repository
from backend.db.models import AuditLog, PaymentRecord
from backend.db.session import get_db

router = APIRouter(tags=["reports"])


def _exception_reason(r: PaymentRecord) -> str:
    """Why this payment is unresolved, in the merchant's words.

    Shared by the per-batch and global exception routes so the two screens can
    never drift into telling different stories about the same payment.
    """
    if r.halted:
        return r.halt_reason or "Halted by a stopping rule."
    if r.escalated:
        return r.escalation_reason or "Escalated to human review."
    return f"Unresolved after {r.attempt_count} attempt(s)."


def _exception_row(r: PaymentRecord) -> dict:
    return {
        "payment_id": r.id,
        "batch_id": r.batch_id,
        "amount": r.amount,
        "failure_type": r.failure_type,
        "reason": _exception_reason(r),
        "attempt_count": r.attempt_count,
        "halted": r.halted,
        "escalated": r.escalated,
    }


def _audit_dict(e: AuditLog) -> dict:
    return {
        "payment_id": e.payment_id,
        "batch_id": e.batch_id,
        "agent": e.agent,
        "action": e.action,
        "reason": e.reason,
        "outcome": e.outcome,
        "timestamp": e.timestamp.isoformat(),
    }


@router.get("/reports/{batch_id}/summary")
async def summary(batch_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    run = await repository.get_batch_run(db, batch_id)
    if run is None:
        raise HTTPException(404, "Unknown batch_id.")
    records = await repository.list_payment_records(db, batch_id)

    by_type: dict[str, dict] = defaultdict(lambda: {"at_risk": 0.0, "recovered": 0.0, "count": 0})
    for r in records:
        key = r.failure_type or "unknown"
        by_type[key]["at_risk"] += r.amount
        by_type[key]["recovered"] += r.recovered_amount or 0.0
        by_type[key]["count"] += 1

    return {
        "total_at_risk": run.total_at_risk,
        "total_recovered": run.total_recovered,
        "recovery_rate": run.recovery_rate,
        "by_failure_type": by_type,
    }


@router.get("/reports/{batch_id}/exceptions")
async def exceptions(batch_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    records = await repository.list_payment_records(db, batch_id)
    return [_exception_row(r) for r in records if not r.recovered]


@router.get("/audit/{payment_id}")
async def audit_trail(payment_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    entries = await repository.get_audit_trail(db, payment_id)
    return [_audit_dict(e) for e in entries]


@router.get("/audit/{batch_id}/export")
async def audit_export(batch_id: str, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    entries = await repository.get_batch_audit(db, batch_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["payment_id", "agent", "action", "reason", "outcome", "timestamp"])
    for e in entries:
        writer.writerow([e.payment_id, e.agent, e.action, e.reason, e.outcome or "", e.timestamp.isoformat()])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_{batch_id}.csv"},
    )


@router.get("/halted/{batch_id}")
async def halted(batch_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await repository.list_halted_actions(db, batch_id)
    return [
        {
            "payment_id": h.payment_id,
            "action": h.action,
            "halt_reason": h.halt_reason,
            "timestamp": h.timestamp.isoformat(),
        }
        for h in rows
    ]


@router.get("/promises/pending")
async def pending_promises(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await repository.list_pending_promises(db)
    return [
        {
            "payment_id": p.payment_id,
            "customer_id": p.customer_id,
            "amount": p.amount,
            "promised_date": p.promised_date.isoformat(),
        }
        for p in rows
    ]


# --- Global (cross-batch) routes -------------------------------------------
# The product screens for Feed / Audit / Halted / Exceptions are not scoped to
# a single batch, so each of these takes an OPTIONAL batch_id filter instead of
# a required path parameter. The per-batch routes above remain for the batch
# results screen.


@router.get("/batches")
async def batches(
    limit: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    runs = await repository.list_batch_runs(db, limit=limit)
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "status": r.status,
            "processed": r.processed,
            "total_records": r.total_records,
            "total_at_risk": r.total_at_risk,
            "total_recovered": r.total_recovered,
            "recovery_rate": r.recovery_rate,
        }
        for r in runs
    ]


@router.get("/audit")
async def audit_search(
    batch_id: str | None = None,
    payment_id: str | None = None,
    agent: str | None = None,
    outcome: str | None = None,
    since: datetime | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    entries = await repository.query_audit_logs(
        db,
        batch_id=batch_id,
        payment_id=payment_id,
        agent=agent,
        outcome=outcome,
        since=since,
        limit=limit,
        offset=offset,
    )
    return [_audit_dict(e) for e in entries]


@router.get("/halted")
async def halted_all(
    batch_id: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await repository.query_halted_actions(db, batch_id=batch_id, limit=limit)
    return [
        {
            "payment_id": h.payment_id,
            "batch_id": h.batch_id,
            "action": h.action,
            "halt_reason": h.halt_reason,
            "amount_at_risk": amount,
            "timestamp": h.timestamp.isoformat(),
        }
        for h, amount in rows
    ]


@router.get("/exceptions")
async def exceptions_all(
    batch_id: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    records = await repository.list_unresolved_records(db, batch_id=batch_id, limit=limit)
    rows = [_exception_row(r) for r in records]
    return {
        "total_unrecovered": sum(r["amount"] for r in rows),
        "count": len(rows),
        "escalated_count": sum(1 for r in rows if r["escalated"]),
        "halted_count": sum(1 for r in rows if r["halted"]),
        "records": rows,
    }


@router.get("/payments/{payment_id}")
async def payment_detail(payment_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Deepest drill-down: one payment's record plus its full decision chain."""
    record = await repository.get_payment_record(db, payment_id)
    entries = await repository.get_audit_trail(db, payment_id)
    if record is None and not entries:
        raise HTTPException(404, "Unknown payment_id.")
    return {
        "record": None
        if record is None
        else {
            "payment_id": record.id,
            "batch_id": record.batch_id,
            "amount": record.amount,
            "customer_id": record.customer_id,
            "failure_type": record.failure_type,
            "root_cause": record.root_cause,
            "intervention": record.intervention,
            "confidence": record.confidence,
            "customer_recovery_score": record.customer_recovery_score,
            "attempt_count": record.attempt_count,
            "recovered": record.recovered,
            "recovered_amount": record.recovered_amount,
            "halted": record.halted,
            "halt_reason": record.halt_reason,
            "escalated": record.escalated,
            "escalation_reason": record.escalation_reason,
            "agent_reasoning": record.agent_reasoning or [],
        },
        "audit_trail": [_audit_dict(e) for e in entries],
    }
