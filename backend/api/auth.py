"""Supabase access-token verification.

The project signs tokens with asymmetric keys (ES256), so this verifies against
the published JWKS and stores no secret. That matters: a shared JWT secret in
the backend is one more credential to leak, and there is no need for one.

Auth is off unless `AUTH_REQUIRED=true`, so a clean checkout still runs with no
credentials — but when it is off the app says so loudly at startup rather than
looking protected while every route answers anonymous callers.

The Razorpay webhook is deliberately exempt: Razorpay authenticates with an
HMAC signature over the body, not a user token, and `verify_webhook_signature`
already rejects anything unsigned.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from backend.config import settings

# auto_error=False so a missing header reaches our own handler and returns a
# message that explains what to do, rather than a bare 403.
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthedUser:
    """Who the request is from. `sub` is the Supabase user id."""

    sub: str
    email: str | None
    role: str | None


class _JwksCache:
    """Caches the signing keys so a request does not fetch them every time.

    PyJWKClient does its own caching, but it is rebuilt whenever the URL
    changes and has no TTL of its own, so key rotation would go unnoticed.
    """

    def __init__(self) -> None:
        self._client: PyJWKClient | None = None
        self._fetched_at = 0.0

    def get(self) -> PyJWKClient:
        now = time.monotonic()
        if self._client is None or (now - self._fetched_at) > settings.auth_jwks_ttl_seconds:
            self._client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
            self._fetched_at = now
        return self._client


_jwks = _JwksCache()


def decode_token(token: str) -> AuthedUser:
    """Verify signature, expiry and audience. Raises jwt exceptions on failure."""
    signing_key = _jwks.get().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        # Supabase issues access tokens with aud "authenticated".
        audience="authenticated",
        options={"require": ["exp", "sub"]},
    )
    return AuthedUser(
        sub=claims["sub"],
        email=claims.get("email"),
        role=claims.get("role"),
    )


async def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthedUser | None:
    """Resolve the caller, or None when auth is switched off.

    Used as a dependency on protected routers. When AUTH_REQUIRED is false this
    returns None and lets the request through, which is what keeps the demo
    runnable without Supabase credentials.
    """
    if not settings.auth_required:
        return None

    if not settings.auth_configured:
        # Fail closed. Being asked to require auth without the means to check it
        # is a misconfiguration, and answering anyway would be the worst option.
        raise HTTPException(
            500, "AUTH_REQUIRED is set but SUPABASE_URL is not configured."
        )

    if credentials is None or not credentials.credentials:
        raise HTTPException(401, "Missing bearer token.")

    try:
        user = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired.") from None
    except (jwt.InvalidTokenError, httpx.HTTPError, Exception) as exc:  # noqa: BLE001
        raise HTTPException(401, f"Invalid token ({type(exc).__name__}).") from None

    request.state.user = user
    return user


def auth_status() -> dict:
    """Surfaced on /api/settings/connection so the UI can be honest about it."""
    return {
        "auth_required": settings.auth_required,
        "auth_configured": settings.auth_configured,
        "provider": "supabase" if settings.auth_configured else None,
    }
