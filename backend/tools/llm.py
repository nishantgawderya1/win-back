"""NVIDIA Nemotron client — the ONLY place an LLM is called.

Nemotron is served through NVIDIA's OpenAI-compatible API
(https://integrate.api.nvidia.com/v1), so we use the `openai` async SDK
pointed at NVIDIA's base_url with an NVIDIA_API_KEY.

This module exposes a single function, diagnose_failure(), used exclusively by
backend/agents/diagnosis.py. The LLM only ever produces reasoning/score fields
— it never issues payment commands or touches ledger values.
"""
from __future__ import annotations

import json

from openai import AsyncOpenAI

from backend.config import settings

_client = AsyncOpenAI(
    api_key=settings.nvidia_api_key,
    base_url=settings.nvidia_base_url,
    timeout=settings.llm_timeout_seconds,
)

_SYSTEM_PROMPT = (
    "You are a payment-recovery diagnosis engine for an Indian merchant on "
    "Razorpay. Given a failed payment, output STRICT JSON with keys: "
    '"root_cause" (one plain-English sentence), '
    '"confidence" (float 0.0-1.0), '
    '"customer_recovery_score" (float 0.0-1.0, likelihood this customer pays '
    "if we intervene, based on their history), and "
    '"reasoning" (array of short strings, the chain of thought). '
    "Respond with JSON only. No markdown, no prose outside the JSON object."
)


def _build_user_prompt(*, failure_type, error_code, amount, hour, prior_payments, prior_recoveries, urgency) -> str:
    return (
        f"Failure type: {failure_type}\n"
        f"Razorpay error code: {error_code}\n"
        f"Amount: INR {amount}\n"
        f"Hour of day (0-23, IST): {hour}\n"
        f"Customer prior payments: {prior_payments}\n"
        f"Customer prior recoveries: {prior_recoveries}\n"
        f"Urgency: {urgency}\n\n"
        "Diagnose the root cause and score recovery likelihood."
    )


async def diagnose_failure(
    *,
    failure_type: str,
    error_code: str | None,
    amount: float,
    hour: int,
    prior_payments: int,
    prior_recoveries: int,
    urgency: str | None,
) -> dict:
    """Return {'root_cause','confidence','customer_recovery_score','reasoning'}.

    Raises on transport/parse failure; the diagnosis node catches and falls
    back to rule-based classification.
    """
    resp = await _client.chat.completions.create(
        model=settings.nemotron_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_prompt(
                    failure_type=failure_type,
                    error_code=error_code,
                    amount=amount,
                    hour=hour,
                    prior_payments=prior_payments,
                    prior_recoveries=prior_recoveries,
                    urgency=urgency,
                ),
            },
        ],
    )
    content = (resp.choices[0].message.content or "").strip()
    return _parse_json(content)


def _parse_json(content: str) -> dict:
    """Nemotron may wrap JSON in ```json fences or emit reasoning first.
    Extract the outermost JSON object defensively."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end != -1:
        content = content[start : end + 1]
    data = json.loads(content)
    return {
        "root_cause": str(data.get("root_cause", "")),
        "confidence": float(data.get("confidence", 0.5)),
        "customer_recovery_score": float(data.get("customer_recovery_score", 0.5)),
        "reasoning": [str(r) for r in data.get("reasoning", [])],
    }
