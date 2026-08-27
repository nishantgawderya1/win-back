"""Reporting routes: summary, exceptions, audit trail, CSV export, halted, promises."""
from __future__ import annotations

import csv
import io
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import repository
from backend.db.session import get_db

router = APIRouter(tags=["reports"])


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
    out = []
    for r in records:
        if r.recovered:
            continue
        reason = (
            r.halt_reason if r.halted
            else r.escalation_reason if r.escalated
            else f"Unresolved after {r.attempt_count} attempt(s)."
        )
        out.append(
            {
                "payment_id": r.id,
                "amount": r.amount,
                "failure_type": r.failure_type,
                "reason": reason,
                "halted": r.halted,
                "escalated": r.escalated,
            }
        )
    return out


@router.get("/audit/{payment_id}")
async def audit_trail(payment_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    entries = await repository.get_audit_trail(db, payment_id)
    return [
        {
            "payment_id": e.payment_id,
            "agent": e.agent,
            "action": e.action,
            "reason": e.reason,
            "outcome": e.outcome,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in entries
    ]


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
