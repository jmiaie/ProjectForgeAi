"""PKCE (RFC 7636) primitives."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class PKCEPair:
    code_verifier: str
    code_challenge: str
    method: str = "S256"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_pkce_pair(verifier_length: int = 64) -> PKCEPair:
    """Return a fresh PKCE verifier + S256 challenge.

    ``verifier_length`` controls the random byte length before base64url
    encoding (RFC 7636 requires the resulting verifier to be 43–128 chars).
    """

    if not 32 <= verifier_length <= 96:
        raise ValueError("verifier_length must be between 32 and 96 bytes")

    verifier = _b64url(secrets.token_bytes(verifier_length))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return PKCEPair(code_verifier=verifier, code_challenge=challenge, method="S256")


def make_state() -> str:
    """Return a 32-byte URL-safe random state token."""

    return _b64url(secrets.token_bytes(32))
