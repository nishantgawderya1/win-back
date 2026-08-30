"""Central configuration. Every env var is typed and validated here.

Never import os.environ anywhere else in the codebase. Always:
    from backend.config import settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Razorpay (test-mode) ---
    razorpay_key_id: str = "rzp_test_placeholder"
    razorpay_key_secret: str = "placeholder_secret"
    razorpay_webhook_secret: str = "placeholder_webhook_secret"
    razorpay_base_url: str = "https://api.razorpay.com/v1"

    # --- LLM: NVIDIA Nemotron (OpenAI-compatible endpoint) ---
    # Nemotron is served through NVIDIA's OpenAI-compatible API. We use the
    # `openai` SDK pointed at this base_url. The model is boxed into the
    # diagnosis node ONLY (see backend/agents/diagnosis.py).
    nvidia_api_key: str = "nvapi-placeholder"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    # Nano tier: diagnosis emits a short root cause plus two scores, so it does
    # not need a frontier model, and one call per record keeps batch latency
    # visible to the user. Verify availability at /v1/models before changing —
    # the previous default reached end of life and failed silently into the
    # rule-based fallback.
    nemotron_model: str = "nvidia/nemotron-3-nano-30b-a3b"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 30.0

    # --- Locale ---
    # Stopping rules and retry windows are merchant-local, not UTC.
    merchant_timezone: str = "Asia/Kolkata"

    # --- Retry scheduler ---
    # A background worker re-enters the graph for payments whose scheduled
    # retry window has arrived. See backend/scheduler.py.
    scheduler_enabled: bool = True
    scheduler_interval_seconds: float = 15.0
    scheduler_batch_limit: int = 50

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./winback.db"

    # --- Stopping rules (overrideable in .env for testing) ---
    max_retry_attempts: int = 3
    min_cooldown_minutes: int = 120
    outreach_cutoff_hour: int = 22          # 10 PM local
    high_value_threshold_inr: float = 50000.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
