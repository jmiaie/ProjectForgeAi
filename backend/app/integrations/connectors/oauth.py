import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

from core.config import settings
from integrations.oauth_state_store import OAuthStateStore


class OAuthConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.state_store = OAuthStateStore()

    def start(self, project_id: str | None = None, redirect_uri: str | None = None) -> dict:
        require_oauth_credentials(self.name)
        state = secrets.token_urlsafe(24)
        code_verifier = secrets.token_urlsafe(48)
        code_challenge = _pkce_challenge(code_verifier)
        scopes = self.config.get("scopes", [])
        callback_uri = redirect_uri or f"{settings.BACKEND_BASE_URL}/api/v1/intake/oauth/{self.name}/callback"
        client_id = _client_id(self.name)
        params = {
            "client_id": client_id,
            "redirect_uri": callback_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }
        self.state_store.create(
            state=state,
            connector_type=self.name,
            code_verifier=code_verifier,
            project_id=project_id,
            redirect_uri=callback_uri,
        )
        return {
            "connector": self.name,
            "type": "oauth",
            "project_id": project_id,
            "state": state,
            "authorization_url": f"{self._authorize_url()}?{urlencode(params)}",
            "redirect_uri": callback_uri,
            "scopes": scopes,
            "pkce": True,
        }

    async def authenticate(self, auth_data: dict):
        code = auth_data.get("code")
        if not code:
            raise ValueError(f"{self.name} requires OAuth code")

        state_payload = self.state_store.consume(auth_data.get("state"))
        if state_payload is None and not settings.OAUTH_ALLOW_UNVERIFIED_STATE:
            raise ValueError("OAuth state is missing, expired, or invalid")

        redirect_uri = state_payload["redirect_uri"] if state_payload else auth_data.get("redirect_uri")
        code_verifier = state_payload["code_verifier"] if state_payload else auth_data.get("code_verifier")
        token_payload = await _exchange_token(
            provider=self.config.get("provider", self.name),
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            connector_name=self.name,
        )
        return {
            "id": f"oauth_{self.name}",
            "provider": self.config.get("provider", self.name),
            "access_token": token_payload["access_token"],
            "refresh_token": token_payload.get("refresh_token"),
            "scopes": self.config.get("scopes", []),
            "account": auth_data.get("account"),
            "token_type": token_payload.get("token_type", "Bearer"),
            "expires_in": token_payload.get("expires_in"),
        }

    async def health(self, connection: dict | None = None) -> dict:
        return {
            "connector": self.name,
            "status": "connected" if connection else "not_connected",
            "checks": {"token_present": bool(connection and connection.get("access_token"))},
        }

    def _authorize_url(self) -> str:
        provider = self.config.get("provider", self.name)
        if provider == "google":
            return "https://accounts.google.com/o/oauth2/v2/auth"
        if provider == "microsoft":
            return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        if provider == "github":
            return "https://github.com/login/oauth/authorize"
        if provider == "slack":
            return "https://slack.com/oauth/v2/authorize"
        return f"https://{provider}.example.com/oauth/authorize"


class APIKeyConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict):
        api_key = auth_data.get("api_key")
        if not api_key:
            raise ValueError(f"{self.name} requires api_key")
        return {
            "id": f"api_key_{self.name}",
            "api_key": api_key,
            "account": auth_data.get("account"),
            "base_url": auth_data.get("base_url"),
            "has_key": True,
        }

    async def health(self, connection: dict | None = None) -> dict:
        return {
            "connector": self.name,
            "status": "connected" if connection else "not_connected",
            "checks": {"api_key_present": bool(connection and connection.get("api_key"))},
        }


def _pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _client_id(connector_name: str) -> str:
    mapping = {
        "google": settings.GOOGLE_OAUTH_CLIENT_ID,
        "microsoft": settings.MICROSOFT_OAUTH_CLIENT_ID,
        "github": settings.GITHUB_OAUTH_CLIENT_ID,
        "slack": settings.SLACK_OAUTH_CLIENT_ID,
    }
    return mapping.get(connector_name) or f"{connector_name}_client_id_placeholder"


def _client_secret(connector_name: str) -> str | None:
    mapping = {
        "google": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "microsoft": settings.MICROSOFT_OAUTH_CLIENT_SECRET,
        "github": settings.GITHUB_OAUTH_CLIENT_SECRET,
        "slack": settings.SLACK_OAUTH_CLIENT_SECRET,
    }
    return mapping.get(connector_name)


def oauth_credentials_configured(connector_name: str) -> bool:
    client_id = _client_id(connector_name)
    client_secret = _client_secret(connector_name)
    return bool(
        client_id
        and client_secret
        and not client_id.endswith("_placeholder")
        and client_secret.strip()
    )


def require_oauth_credentials(connector_name: str) -> None:
    if settings.OAUTH_MOCK_TOKEN_EXCHANGE:
        return
    if not oauth_credentials_configured(connector_name):
        raise ValueError(
            f"{connector_name} OAuth credentials are not configured. "
            f"Set {connector_name.upper()}_OAUTH_CLIENT_ID and "
            f"{connector_name.upper()}_OAUTH_CLIENT_SECRET, or enable OAUTH_MOCK_TOKEN_EXCHANGE."
        )


def _token_url(provider: str) -> str:
    if provider == "google":
        return "https://oauth2.googleapis.com/token"
    if provider == "microsoft":
        return "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    if provider == "github":
        return "https://github.com/login/oauth/access_token"
    if provider == "slack":
        return "https://slack.com/api/oauth.v2.access"
    return f"https://{provider}.example.com/oauth/token"


async def _exchange_token(
    *,
    provider: str,
    code: str,
    redirect_uri: str | None,
    code_verifier: str | None,
    connector_name: str,
) -> dict:
    client_id = _client_id(connector_name)
    client_secret = _client_secret(connector_name)
    if settings.OAUTH_MOCK_TOKEN_EXCHANGE:
        return {
            "access_token": f"mock_access_{code[:12]}",
            "refresh_token": f"mock_refresh_{code[:12]}",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    if not oauth_credentials_configured(connector_name):
        raise ValueError(
            f"{connector_name} OAuth credentials are not configured for production token exchange"
        )

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if code_verifier:
        data["code_verifier"] = code_verifier

    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(_token_url(provider), data=data, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if "access_token" not in payload:
            raise ValueError(f"{connector_name} token exchange did not return access_token")
        return payload
