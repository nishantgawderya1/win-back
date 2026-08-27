"""Batch orchestration — runs the graph over N payment records.

Neither the graph nor the API routes own the batch loop; this does. Called as a
FastAPI background task from POST /batch/upload.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from backend.db.repository import bump_batch_progress, finalize_batch, list_payment_records
from backend.db.session import async_session_factory
from backend.graph.graph import app_graph
from backend.graph.state import WinBackState


async def run_one(state: WinBackState) -> WinBackState:
    """Invoke the graph for a single payment. Returns terminal state as a model."""
    result = await app_graph.ainvoke(state)
    # LangGraph returns a dict-like; coerce back to the Pydantic model.
    return WinBackState.model_validate(result)


async def run_batch(batch_id: str, states: list[WinBackState]) -> None:
    """Process every record, updating progress, then finalize batch metrics."""
    for state in states:
        try:
            await run_one(state)
        except Exception as exc:  # noqa: BLE001 — one bad record shouldn't kill the batch
            print(f"[runner] payment {state.payment_id} failed: {exc!r}")
        finally:
            async with async_session_factory() as db:
                await bump_batch_progress(db, batch_id)
        await asyncio.sleep(0)  # yield to the event loop / WS broadcasts

    await _finalize(batch_id)


async def _finalize(batch_id: str) -> None:
    async with async_session_factory() as db:
        records = await list_payment_records(db, batch_id)
        total_at_risk = sum(r.amount for r in records)
        total_recovered = sum(r.recovered_amount or 0.0 for r in records if r.recovered)
        rate = (total_recovered / total_at_risk) if total_at_risk else 0.0
        await finalize_batch(db, batch_id, total_at_risk, total_recovered, rate)
    print(f"[runner] batch {batch_id} complete at {datetime.utcnow().isoformat()}")
