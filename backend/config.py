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
    # Verify availability at /v1/models before changing this — a retired model
    # returns 410 and every diagnosis degrades silently to the rule-based
    # fallback, which is exactly how the previous default went unnoticed.
    nemotron_model: str = "nvidia/nemotron-3-super-120b-a12b"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 60.0
    # Nemotron reasons before answering unless told not to. Measured on the
    # diagnosis prompt: 10.4s thinking on, 6.1s left unspecified, 3.3s off.
    # Diagnosis wants one sentence and two scores, and already returns its own
    # reasoning array, so the extra latency buys little across a 75-record
    # batch. Turn it on to capture the model's full chain into the audit trail.
    llm_enable_thinking: bool = False

    # --- Auth (Supabase) ---
    # Tokens are signed with the project's asymmetric keys, so the backend
    # verifies against the public JWKS and holds no secret of its own.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    # Off by default so a clean checkout runs without credentials. Turn it on
    # and every route except the health check and the Razorpay webhook demands
    # a valid access token.
    auth_required: bool = False
    auth_jwks_ttl_seconds: float = 3600.0

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def auth_configured(self) -> bool:
        return bool(self.supabase_url)

    # --- Locale ---
    # Stopping rules and retry windows are merchant-local, not UTC.
    merchant_timezone: str = "Asia/Kolkata"

    # --- Batch processing ---
    # Payments are independent, and the diagnosis call is almost entirely
    # network wait, so the batch runs them concurrently. Bounded because each
    # slot holds an LLM call and a SQLite write.
    batch_concurrency: int = 8

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
