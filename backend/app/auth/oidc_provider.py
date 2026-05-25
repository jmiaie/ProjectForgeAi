import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from core.config import settings


class OIDCStateStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.AUTH_SESSION_ROOT) / "oidc_states"
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, *, state: str, redirect_after: str | None = None) -> dict[str, Any]:
        payload = {
            "state": state,
            "redirect_after": redirect_after,
            "created_at": datetime.now(UTC).isoformat(),
        }
        (self.root / f"{state}.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload

    def consume(self, state: str | None) -> dict[str, Any] | None:
        if not state:
            return None
        path = self.root / f"{state}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        path.unlink(missing_ok=True)
        created_at = datetime.fromisoformat(payload["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at + timedelta(minutes=15) < datetime.now(UTC):
            return None
        return payload


class OIDCProvider:
    def __init__(self):
        self.state_store = OIDCStateStore()
        self._metadata_cache: dict[str, Any] | None = None

    @property
    def enabled(self) -> bool:
        return settings.OIDC_ENABLED

    @property
    def mock_mode(self) -> bool:
        return settings.OIDC_MOCK

    @property
    def redirect_uri(self) -> str:
        return settings.OIDC_REDIRECT_URI or f"{settings.BACKEND_BASE_URL}/api/v1/auth/callback"

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "mock_mode": self.mock_mode,
            "issuer": settings.OIDC_ISSUER,
            "client_id": settings.OIDC_CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "scopes": settings.OIDC_SCOPES,
            "configured": self.is_configured(),
        }

    def is_configured(self) -> bool:
        if not self.enabled:
            return False
        if self.mock_mode:
            return True
        return bool(settings.OIDC_ISSUER and settings.OIDC_CLIENT_ID and settings.OIDC_CLIENT_SECRET)

    def group_role_map(self) -> dict[str, str]:
        if not settings.OIDC_GROUP_ROLE_MAP:
            return {}
        try:
            parsed = json.loads(settings.OIDC_GROUP_ROLE_MAP)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {str(key): str(value).lower() for key, value in parsed.items()}

    def resolve_role(self, groups: list[str] | None) -> str:
        role_map = self.group_role_map()
        for group in groups or []:
            mapped = role_map.get(group)
            if mapped:
                return mapped
        return settings.OIDC_DEFAULT_ROLE

    def start_login(self, redirect_after: str | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise ValueError("OIDC is not enabled")
        if self.mock_mode:
            return {
                "mode": "mock",
                "message": "Use POST /api/v1/auth/mock-login for development SSO",
                "redirect_after": redirect_after or settings.FRONTEND_BASE_URL,
            }

        if not self.is_configured():
            raise ValueError("OIDC issuer and client credentials are required")

        state = secrets.token_urlsafe(24)
        self.state_store.create(state=state, redirect_after=redirect_after)
        params = {
            "client_id": settings.OIDC_CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": settings.OIDC_SCOPES,
            "state": state,
        }
        authorize_url = f"{settings.OIDC_ISSUER.rstrip('/')}/authorize?{urlencode(params)}"
        return {
            "mode": "oidc",
            "state": state,
            "authorization_url": authorize_url,
            "redirect_uri": self.redirect_uri,
        }

    async def exchange_code(self, code: str, state: str | None) -> dict[str, Any]:
        state_payload = self.state_store.consume(state)
        if state_payload is None:
            raise ValueError("OIDC state is missing, expired, or invalid")

        token_url = f"{settings.OIDC_ISSUER.rstrip('/')}/token"
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": settings.OIDC_CLIENT_ID,
                    "client_secret": settings.OIDC_CLIENT_SECRET,
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_payload = token_response.json()

            userinfo = await self._fetch_userinfo(client, token_payload)
        groups = _extract_groups(userinfo)
        actor_id = str(userinfo.get("sub") or userinfo.get("email") or userinfo.get("preferred_username"))
        return {
            "actor_id": actor_id,
            "email": userinfo.get("email"),
            "groups": groups,
            "role": self.resolve_role(groups),
            "redirect_after": state_payload.get("redirect_after"),
            "userinfo": userinfo,
        }

    async def _fetch_userinfo(self, client: httpx.AsyncClient, token_payload: dict[str, Any]) -> dict[str, Any]:
        userinfo_url = f"{settings.OIDC_ISSUER.rstrip('/')}/userinfo"
        access_token = token_payload.get("access_token")
        if not access_token:
            raise ValueError("OIDC token response missing access_token")

        response = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("OIDC userinfo response must be a JSON object")
        return payload


def _extract_groups(userinfo: dict[str, Any]) -> list[str]:
    groups = userinfo.get("groups")
    if isinstance(groups, list):
        return [str(group) for group in groups]
    roles = userinfo.get("roles")
    if isinstance(roles, list):
        return [str(role) for role in roles]
    return []
