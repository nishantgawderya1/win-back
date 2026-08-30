"""Batch upload + status + results routes."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import repository
from backend.db.session import get_db
from backend.graph.state import WinBackState
from backend.runner import run_batch

router = APIRouter(prefix="/batch", tags=["batch"])


def _row_to_state(row: dict, batch_id: str) -> WinBackState:
    def _f(key: str, default: float = 0.0) -> float:
        try:
            return float(row.get(key) or default)
        except (TypeError, ValueError):
            return default

    def _i(key: str, default: int = 0) -> int:
        try:
            return int(float(row.get(key) or default))
        except (TypeError, ValueError):
            return default

    failed_at = None
    if row.get("failed_at"):
        try:
            failed_at = datetime.fromisoformat(row["failed_at"])
        except ValueError:
            failed_at = None

    return WinBackState(
        payment_id=row.get("payment_id") or f"pay_{uuid.uuid4().hex[:10]}",
        batch_id=batch_id,
        amount=_f("amount"),
        customer_id=row.get("customer_id") or "cust_unknown",
        customer_name=row.get("customer_name"),
        customer_phone=row.get("customer_phone"),
        customer_email=row.get("customer_email"),
        razorpay_error_code=row.get("razorpay_error_code") or None,
        prior_payments=_i("prior_payments"),
        prior_recoveries=_i("prior_recoveries"),
        customer_opted_out=str(row.get("customer_opted_out", "")).strip().lower()
        in ("1", "true", "yes"),
        failed_at=failed_at,
    )


@router.post("/upload")
async def upload_batch(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    states = [_row_to_state(row, batch_id) for row in reader]
    if not states:
        raise HTTPException(400, "CSV contained no rows.")

    await repository.create_batch_run(db, batch_id, len(states))
    background.add_task(run_batch, batch_id, states)

    return {"batch_id": batch_id, "record_count": len(states), "status": "processing"}


@router.get("/{batch_id}/status")
async def batch_status(batch_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    run = await repository.get_batch_run(db, batch_id)
    if run is None:
        raise HTTPException(404, "Unknown batch_id.")
    return {
        "status": run.status,
        "processed": run.processed,
        "total": run.total_records,
    }


@router.get("/{batch_id}/results")
async def batch_results(batch_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    run = await repository.get_batch_run(db, batch_id)
    if run is None:
        raise HTTPException(404, "Unknown batch_id.")
    records = await repository.list_payment_records(db, batch_id)
    return {
        "batch": {
            "id": run.id,
            "status": run.status,
            "total_records": run.total_records,
            "total_at_risk": run.total_at_risk,
            "total_recovered": run.total_recovered,
            "recovery_rate": run.recovery_rate,
        },
        "records": [
            {
                "payment_id": r.id,
                "amount": r.amount,
                "failure_type": r.failure_type,
                "root_cause": r.root_cause,
                "intervention": r.intervention,
                "attempt_count": r.attempt_count,
                "recovered": r.recovered,
                "recovered_amount": r.recovered_amount,
                "halted": r.halted,
                "halt_reason": r.halt_reason,
                "escalated": r.escalated,
                "escalation_reason": r.escalation_reason,
                "customer_recovery_score": r.customer_recovery_score,
                "confidence": r.confidence,
                "agent_reasoning": r.agent_reasoning or [],
            }
            for r in records
        ],
    }
