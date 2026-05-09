"""Symmetric encryption for at-rest secrets.

We derive a 32-byte Fernet key from ``Settings.ENCRYPTION_KEY`` so operators
can rotate the secret without writing migrations against bytes-typed columns.
If ``cryptography`` is not installed we fall back to a clearly-marked base64
encoding so development workflows still function — production deployments
must install the dependency and rotate the key.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency at scaffold stage
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment, misc]


_DEV_PREFIX = "dev$"


def derive_fernet_key(secret: str) -> bytes:
    """Return a URL-safe base64 32-byte Fernet key derived from ``secret``."""

    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _fernet() -> "Fernet | None":
    if Fernet is None:
        logger.warning(
            "cryptography is not installed; encryption helper using INSECURE base64 fallback"
        )
        return None
    settings = get_settings()
    return Fernet(derive_fernet_key(settings.ENCRYPTION_KEY))


def encrypt_text(plaintext: str) -> str:
    """Encrypt a UTF-8 string and return a token suitable for column storage."""

    cipher = _fernet()
    if cipher is None:
        return _DEV_PREFIX + base64.urlsafe_b64encode(plaintext.encode("utf-8")).decode("ascii")
    return cipher.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_text(token: str) -> str:
    """Inverse of :func:`encrypt_text`."""

    if token.startswith(_DEV_PREFIX):
        return base64.urlsafe_b64decode(token[len(_DEV_PREFIX):].encode("ascii")).decode("utf-8")
    cipher = _fernet()
    if cipher is None:
        raise RuntimeError("cryptography is required to decrypt non-dev tokens")
    try:
        return cipher.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - defensive
        raise ValueError("Invalid or tampered ciphertext") from exc


def reset_cipher_cache() -> None:
    """Clear the cached Fernet instance (used when ENCRYPTION_KEY changes)."""

    _fernet.cache_clear()
