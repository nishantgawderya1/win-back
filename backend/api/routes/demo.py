"""Demo clock — fast-forward the agent so the retry ladder is observable.

The planner schedules retries honestly: 9 AM tomorrow for a UPI timeout, the
1st of next month for insufficient funds. Those are the right windows and they
are also unwatchable in a demo. Rather than shrink the real intervals (which
would make tools/retry_timing a lie), this moves a virtual clock forward for
the whole agent at once, so the retries that were already scheduled simply come
due. Cooldowns, quiet hours and retry windows all shift together and stay
mutually consistent.

Nothing here bypasses a stopping rule. Advancing the clock only changes what
time the agent thinks it is; the planner still runs every guardrail before it
acts on anything the scheduler hands back.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.scheduler import run_due_retries
from backend.tools import clock

router = APIRouter(prefix="/demo", tags=["demo"])


class AdvanceRequest(BaseModel):
    """Move the clock forward. Combine fields freely; they add up."""

    days: int = Field(0, ge=0, le=400)
    hours: int = Field(0, ge=0, le=10000)
    minutes: int = Field(0, ge=0, le=100000)
    # Process the queue straight away rather than waiting for the next tick.
    run_due: bool = True


@router.get("/clock")
async def get_clock() -> dict:
    return clock.status()


@router.post("/advance")
async def advance_clock(payload: AdvanceRequest) -> dict:
    delta = timedelta(days=payload.days, hours=payload.hours, minutes=payload.minutes)
    if delta == timedelta(0):
        return {**clock.status(), "advanced_by_seconds": 0, "scheduler": None}

    clock.advance(delta)
    result = await run_due_retries() if payload.run_due else None
    return {**clock.status(), "advanced_by_seconds": delta.total_seconds(), "scheduler": result}


@router.post("/reset")
async def reset_clock() -> dict:
    clock.reset()
    return clock.status()


@router.post("/run-due")
async def run_due() -> dict:
    """Force a scheduler pass without touching the clock."""
    return {**clock.status(), "scheduler": await run_due_retries()}
