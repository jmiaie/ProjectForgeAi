"""OAuth 2.0 / PKCE connector.

This is a scaffold: the actual token exchange depends on per-provider client
IDs, secrets, and redirect URIs which are wired in via environment variables.
The class is structured so the real implementation can drop in without
changing call sites.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - optional dependency at scaffold stage
    from authlib.integrations.starlette_client import OAuth  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    OAuth = None  # type: ignore[assignment]


class OAuthConnector:
    """Generic OAuth 2.0 connector backed by Authlib when available."""

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict[str, Any]) -> dict[str, Any]:
        """Exchange ``auth_data`` (code/state/PKCE) for an access token.

        The scaffold echoes the inbound code so end-to-end wiring can be
        verified before live OAuth credentials are configured.
        """

        code = auth_data.get("code")
        state = auth_data.get("state")
        return {
            "id": f"oauth_{self.name}",
            "provider": self.config.get("provider", self.name),
            "scopes": self.config.get("scopes", []),
            "code": code,
            "state": state,
            "token": auth_data.get("token") or code,
        }
