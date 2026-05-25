import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.config import settings


class AuthSessionStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.AUTH_SESSION_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        actor_id: str,
        email: str | None = None,
        role: str = "viewer",
        groups: list[str] | None = None,
        provider: str = "oidc",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.AUTH_SESSION_TTL_SECONDS)
        session = {
            "token": token,
            "actor_id": actor_id,
            "email": email,
            "role": role.lower(),
            "groups": groups or [],
            "provider": provider,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        path = self.root / f"{token}.json"
        path.write_text(json.dumps(session, indent=2, sort_keys=True))
        return session

    def get(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        path = self.root / f"{token}.json"
        if not path.exists():
            return None
        session = json.loads(path.read_text())
        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            path.unlink(missing_ok=True)
            return None
        return session

    def revoke(self, token: str | None) -> bool:
        if not token:
            return False
        path = self.root / f"{token}.json"
        if not path.exists():
            return False
        os.remove(path)
        return True

    def count_active(self) -> int:
        now = datetime.now(UTC)
        count = 0
        for path in self.root.glob("*.json"):
            try:
                session = json.loads(path.read_text())
                expires_at = datetime.fromisoformat(session["expires_at"])
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if expires_at >= now:
                    count += 1
                else:
                    path.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError, ValueError):
                path.unlink(missing_ok=True)
        return count
