"""Static OAuth provider metadata.

Only well-known endpoints are baked in. Per-deployment values like
``client_id`` and ``client_secret`` come from environment via
:class:`app.core.config.Settings`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OAuthProviderMetadata:
    name: str
    authorize_url: str
    token_url: str
    default_scopes: tuple[str, ...]
    use_pkce: bool = True
    audience: str | None = None
    extra_authorize_params: dict[str, str] | None = None


PROVIDERS: dict[str, OAuthProviderMetadata] = {
    "google": OAuthProviderMetadata(
        name="google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        default_scopes=(
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ),
        extra_authorize_params={"access_type": "offline", "prompt": "consent"},
    ),
    "microsoft": OAuthProviderMetadata(
        name="microsoft",
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        default_scopes=(
            "openid",
            "profile",
            "offline_access",
            "Mail.Read",
            "Calendars.Read",
            "Files.Read",
        ),
    ),
    "github": OAuthProviderMetadata(
        name="github",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        default_scopes=("repo", "read:org"),
        use_pkce=False,
    ),
    "slack": OAuthProviderMetadata(
        name="slack",
        authorize_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        default_scopes=("channels:read", "chat:write"),
        use_pkce=False,
    ),
}


def get_provider_metadata(name: str) -> OAuthProviderMetadata:
    metadata = PROVIDERS.get(name)
    if metadata is None:
        raise ValueError(f"Unknown OAuth provider: {name}")
    return metadata
