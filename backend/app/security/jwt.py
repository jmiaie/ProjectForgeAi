"""JWT encode / decode helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import jwt  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    jwt = None  # type: ignore[assignment]


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or is no longer valid."""


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Create a signed JWT access token for ``subject`` (typically user id)."""

    if jwt is None:  # pragma: no cover
        raise RuntimeError("PyJWT is required to create access tokens")
    settings = get_settings()
    now = datetime.now(timezone.utc)
    minutes = expires_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "iss": settings.JWT_ISSUER,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode + validate a JWT, returning the claims dict."""

    if jwt is None:  # pragma: no cover
        raise RuntimeError("PyJWT is required to decode access tokens")
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
    except Exception as exc:
        raise TokenError(str(exc)) from exc
