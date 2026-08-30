"""Runtime-mutable stopping rules.

The four stopping-rule thresholds are the one piece of configuration a merchant
edits from inside the product (Settings screen), so they cannot live in the
frozen pydantic-settings singleton. This module holds a mutable object that is
seeded from `settings` and then overridden from the DB row at startup.

Everything else stays in backend/config.py. Never import os.environ here.

    from backend.config_runtime import runtime_rules
    if state.attempt_count >= runtime_rules.max_retry_attempts: ...
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from backend.config import settings


@dataclass
class RuntimeRules:
    """The live values the planner enforces. Seeded from settings, then DB."""

    max_retry_attempts: int
    min_cooldown_minutes: int
    outreach_cutoff_hour: int
    high_value_threshold_inr: float

    @classmethod
    def from_settings(cls) -> RuntimeRules:
        return cls(
            max_retry_attempts=settings.max_retry_attempts,
            min_cooldown_minutes=settings.min_cooldown_minutes,
            outreach_cutoff_hour=settings.outreach_cutoff_hour,
            high_value_threshold_inr=settings.high_value_threshold_inr,
        )

    def apply(
        self,
        *,
        max_retry_attempts: int,
        min_cooldown_minutes: int,
        outreach_cutoff_hour: int,
        high_value_threshold_inr: float,
    ) -> None:
        """Mutate in place — callers hold a reference to this singleton."""
        self.max_retry_attempts = max_retry_attempts
        self.min_cooldown_minutes = min_cooldown_minutes
        self.outreach_cutoff_hour = outreach_cutoff_hour
        self.high_value_threshold_inr = high_value_threshold_inr

    def as_dict(self) -> dict:
        return asdict(self)


# Module-level singleton. Seeded from settings so the defaults are identical to
# the .env contract; overridden from the DB in the app lifespan.
runtime_rules = RuntimeRules.from_settings()
