"""OAuth 2.0 / PKCE flow orchestration.

Builds the authorize URL (storing CSRF state + PKCE verifier server-side)
and performs the token exchange in the callback.

The token exchange uses ``httpx.AsyncClient``. Tests can monkey-patch the
``_post_token_exchange`` method (or pass a custom ``http_client``) to avoid
hitting real provider endpoints.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    Settings,
    get_oauth_client_credentials,
    get_settings,
)
from app.db.models import OAuthState
from app.integrations.oauth.pkce import generate_pkce_pair, make_state
from app.integrations.oauth.providers import (
    OAuthProviderMetadata,
    get_provider_metadata,
)

logger = logging.getLogger(__name__)


class OAuthFlowError(Exception):
    """Raised when the OAuth flow fails (config, state, or token exchange)."""


@dataclass
class OAuthAuthorization:
    authorize_url: str
    state: str
    redirect_uri: str
    provider: str


@dataclass
class OAuthTokenResponse:
    provider: str
    access_token: str
    token_type: str = "Bearer"
    refresh_token: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    raw: dict[str, Any] | None = None
    obtained_at: datetime | None = None

    def to_metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "scope": self.scope,
            "obtained_at": (
                self.obtained_at or datetime.now(timezone.utc)
            ).isoformat(),
            "has_refresh_token": self.refresh_token is not None,
        }


class OAuthFlow:
    """Stateful OAuth flow service backed by the database."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        http_client: Any | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self._http_client = http_client

    # ------------------------------------------------------------------
    # Authorize
    # ------------------------------------------------------------------
    async def begin_authorize(
        self,
        provider: str,
        *,
        project_id: str | None = None,
        scopes: list[str] | None = None,
        final_redirect: str | None = None,
    ) -> OAuthAuthorization:
        metadata = get_provider_metadata(provider)
        client_id, _ = get_oauth_client_credentials(self.settings, provider)
        if not client_id:
            raise OAuthFlowError(
                f"OAuth provider '{provider}' is not configured "
                f"(set {provider.upper()}_CLIENT_ID / _CLIENT_SECRET)"
            )

        state = make_state()
        redirect_uri = self._redirect_uri(provider)
        pkce = generate_pkce_pair() if metadata.use_pkce else None

        record = OAuthState(
            state=state,
            provider=provider,
            code_verifier=pkce.code_verifier if pkce else None,
            project_id=project_id,
            redirect_uri=redirect_uri,
            final_redirect=final_redirect,
        )
        self.session.add(record)
        await self.session.flush()

        params: dict[str, str] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or metadata.default_scopes),
            "state": state,
        }
        if pkce is not None:
            params["code_challenge"] = pkce.code_challenge
            params["code_challenge_method"] = pkce.method
        if metadata.extra_authorize_params:
            params.update(metadata.extra_authorize_params)

        authorize_url = f"{metadata.authorize_url}?{urlencode(params)}"
        return OAuthAuthorization(
            authorize_url=authorize_url,
            state=state,
            redirect_uri=redirect_uri,
            provider=provider,
        )

    # ------------------------------------------------------------------
    # Callback / exchange
    # ------------------------------------------------------------------
    async def consume_state(self, state: str) -> OAuthState:
        stmt = select(OAuthState).where(OAuthState.state == state)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise OAuthFlowError("Unknown or already-used OAuth state")
        if record.is_expired(self.settings.OAUTH_STATE_TTL_SECONDS):
            await self.session.delete(record)
            await self.session.flush()
            raise OAuthFlowError("OAuth state has expired; restart the flow")
        await self.session.delete(record)
        await self.session.flush()
        return record

    async def exchange_code(
        self, *, provider: str, code: str, state_record: OAuthState
    ) -> OAuthTokenResponse:
        metadata = get_provider_metadata(provider)
        client_id, client_secret = get_oauth_client_credentials(
            self.settings, provider
        )
        if not client_id or not client_secret:
            raise OAuthFlowError(
                f"OAuth provider '{provider}' is missing client credentials"
            )

        payload: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": state_record.redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if state_record.code_verifier:
            payload["code_verifier"] = state_record.code_verifier

        body = await self._post_token_exchange(metadata.token_url, payload)
        access_token = body.get("access_token")
        if not access_token:
            raise OAuthFlowError(
                f"Provider '{provider}' did not return an access_token: "
                f"{body.get('error') or body}"
            )
        return OAuthTokenResponse(
            provider=provider,
            access_token=access_token,
            token_type=body.get("token_type", "Bearer"),
            refresh_token=body.get("refresh_token"),
            expires_in=body.get("expires_in"),
            scope=body.get("scope"),
            raw=body,
            obtained_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _redirect_uri(self, provider: str) -> str:
        base = self.settings.OAUTH_REDIRECT_BASE_URL.rstrip("/")
        return f"{base}/api/v1/intake/oauth/{provider}/callback"

    async def _post_token_exchange(
        self, token_url: str, payload: dict[str, str]
    ) -> dict[str, Any]:
        """Issue the token-exchange POST. Test hook: monkey-patch this method."""

        client = self._http_client
        owns_client = False
        if client is None:
            try:
                import httpx  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover
                raise OAuthFlowError(
                    "httpx is required for OAuth token exchange"
                ) from exc
            client = httpx.AsyncClient(timeout=10.0)
            owns_client = True

        try:
            response = await client.post(
                token_url,
                data=payload,
                headers={"Accept": "application/json"},
            )
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code >= 400:
            raise OAuthFlowError(
                f"Token exchange failed ({response.status_code}): {response.text}"
            )
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise OAuthFlowError(
                f"Token endpoint returned non-JSON body: {response.text}"
            ) from exc
