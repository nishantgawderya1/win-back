"""Settings routes: stopping rules (read/write) and connection status.

Stopping rules are the one piece of config a merchant edits from the product,
so they live in backend/config_runtime.runtime_rules — mutated here and
persisted so the change survives a restart. Everything else stays read-only,
sourced from .env via backend.config.settings.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import auth_status
from backend.config import settings
from backend.config_runtime import runtime_rules
from backend.db import repository
from backend.db.session import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


class RuleUpdate(BaseModel):
    """Bounds mirror what the planner can meaningfully enforce."""

    max_retry_attempts: int = Field(ge=1, le=10)
    min_cooldown_minutes: int = Field(ge=0, le=1440)
    outreach_cutoff_hour: int = Field(ge=0, le=23)
    high_value_threshold_inr: float = Field(ge=0)


def _mask(value: str, keep: int = 4) -> str:
    """rzp_test_abcd1234 -> rzp_test_****1234. Never echo a full credential."""
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return f"{value[:9]}****{value[-keep:]}" if len(value) > 13 else f"****{value[-keep:]}"


@router.get("/rules")
async def get_rules(db: AsyncSession = Depends(get_db)) -> dict:
    row = await repository.get_rule_config(db)
    return {
        **runtime_rules.as_dict(),
        "source": "saved" if row else "env_defaults",
        "updated_at": row.updated_at.isoformat() if row else None,
    }


@router.put("/rules")
async def put_rules(payload: RuleUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    """Persist, then mutate the in-process singleton so the change is live for
    the very next payment — no restart, no re-read."""
    row = await repository.save_rule_config(db, **payload.model_dump())
    runtime_rules.apply(**payload.model_dump())
    return {
        **runtime_rules.as_dict(),
        "source": "saved",
        "updated_at": row.updated_at.isoformat(),
    }


@router.get("/connection")
async def get_connection(request: Request) -> dict:
    """Masked Razorpay identity + the webhook URL to paste into their dashboard."""
    base = str(request.base_url).rstrip("/")
    key_id = settings.razorpay_key_id
    # Resolved once at startup; None only if the app was built without lifespan.
    llm_status = getattr(request.app.state, "llm_status", None)
    return {
        "razorpay_key_id_masked": _mask(key_id),
        "test_mode": key_id.startswith("rzp_test"),
        "webhook_url": f"{base}/api/webhook/razorpay",
        "webhook_events": ["payment.failed", "subscription.charged.failed"],
        "llm_model": settings.nemotron_model,
        "llm_base_url": settings.nvidia_base_url,
        "llm_key_configured": not settings.nvidia_api_key.endswith("placeholder"),
        "llm_model_available": None if llm_status is None else llm_status["ok"],
        "llm_status_reason": None if llm_status is None else llm_status["reason"],
        "merchant_timezone": settings.merchant_timezone,
        "scheduler_enabled": settings.scheduler_enabled,
        **auth_status(),
    }
