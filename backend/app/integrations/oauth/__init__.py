"""Real OAuth 2.0 / PKCE flow primitives.

This package owns provider metadata, PKCE generation, and the high-level
``OAuthFlow`` service. It is intentionally separate from
``app.integrations.connectors.oauth`` so the legacy connector keeps the
"stub on missing config" behaviour while the new flow drives the real
authorize / token-exchange round-trip.
"""

from app.integrations.oauth.flow import (
    OAuthFlow,
    OAuthFlowError,
    OAuthTokenResponse,
)
from app.integrations.oauth.pkce import generate_pkce_pair
from app.integrations.oauth.providers import (
    OAuthProviderMetadata,
    PROVIDERS,
    get_provider_metadata,
)

__all__ = [
    "OAuthFlow",
    "OAuthFlowError",
    "OAuthProviderMetadata",
    "OAuthTokenResponse",
    "PROVIDERS",
    "generate_pkce_pair",
    "get_provider_metadata",
]
