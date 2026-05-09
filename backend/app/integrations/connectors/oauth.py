import secrets
from urllib.parse import urlencode

from core.config import settings


class OAuthConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    def start(self, project_id: str | None = None, redirect_uri: str | None = None) -> dict:
        state = secrets.token_urlsafe(24)
        scopes = self.config.get("scopes", [])
        callback_uri = redirect_uri or f"{settings.BACKEND_BASE_URL}/api/v1/intake/oauth/{self.name}/callback"
        params = {
            "client_id": f"{self.name}_client_id_placeholder",
            "redirect_uri": callback_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return {
            "connector": self.name,
            "type": "oauth",
            "project_id": project_id,
            "state": state,
            "authorization_url": f"{self._authorize_url()}?{urlencode(params)}",
            "redirect_uri": callback_uri,
            "scopes": scopes,
        }

    async def authenticate(self, auth_data: dict):
        code = auth_data.get("code")
        if not code:
            raise ValueError(f"{self.name} requires OAuth code")
        return {
            "id": f"oauth_{self.name}",
            "provider": self.config.get("provider", self.name),
            "access_token": f"placeholder_access_{code}",
            "refresh_token": auth_data.get("refresh_token"),
            "scopes": self.config.get("scopes", []),
            "account": auth_data.get("account"),
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
