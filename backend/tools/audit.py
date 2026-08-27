"""Audit logging = the product, not a byproduct.

log_action() does three things in one call:
  1. persists an AuditLog row (the audit trail)
  2. broadcasts an agent_action event over /ws/feed (the live feed)
  3. returns an AuditEntry the node appends to state.audit_log

Every agent node calls this at the START and END of its work.
"""
from __future__ import annotations

from datetime import datetime, timezone

from backend.api.ws_manager import manager
from backend.db.session import async_session_factory
from backend.graph.state import AuditEntry, WinBackState
from backend.db import repository


async def log_action(
    state: WinBackState,
    agent: str,
    action: str,
    reason: str,
    outcome: str | None = None,
) -> AuditEntry:
    """Persist + broadcast a single agent action. Safe to call from any node."""
    # Persist in its own short-lived session so nodes stay DB-free.
    async with async_session_factory() as db:
        await repository.add_audit_log(
            db,
            payment_id=state.payment_id,
            batch_id=state.batch_id,
            agent=agent,
            action=action,
            reason=reason,
            outcome=outcome,
        )

    event = {
        "event_type": "agent_action",
        "payment_id": state.payment_id,
        "batch_id": state.batch_id,
        "agent": agent,
        "action": action,
        "reason": reason,
        "outcome": outcome,
        "amount": state.amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast(event)

    return AuditEntry(agent=agent, action=action, reason=reason, outcome=outcome)
