"""Password hashing helpers (bcrypt)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import bcrypt  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    bcrypt = None  # type: ignore[assignment]


_BCRYPT_MAX_BYTES = 72  # bcrypt silently truncates beyond 72 bytes


def hash_password(password: str) -> str:
    """Hash ``password`` with bcrypt, returning a portable string token."""

    if bcrypt is None:  # pragma: no cover - dev fallback
        raise RuntimeError("bcrypt is required for password hashing")
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        encoded = encoded[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time comparison of ``password`` against an existing hash."""

    if bcrypt is None:  # pragma: no cover
        raise RuntimeError("bcrypt is required for password verification")
    if not hashed:
        return False
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        encoded = encoded[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(encoded, hashed.encode("ascii"))
    except ValueError as exc:
        logger.warning("verify_password got malformed hash: %s", exc)
        return False
