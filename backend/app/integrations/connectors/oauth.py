from __future__ import annotations

import hashlib
import os
import secrets
from urllib.parse import urlencode


class OAuthConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    def _client_id(self) -> str:
        env_key = self.config.get("client_id_env")
        if env_key:
            return os.getenv(env_key, "demo-client-id")
        return "demo-client-id"

    def _client_secret(self) -> str:
        env_key = self.config.get("client_secret_env")
        if env_key:
            return os.getenv(env_key, "")
        return ""

    def build_authorization_url(self, *, redirect_uri: str, state: str, code_challenge: str) -> str:
        auth_base = self.config.get("authorization_url", "")
        scope_values = self.config.get("scopes", [])
        query = {
            "client_id": self._client_id(),
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scope_values),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{auth_base}?{urlencode(query)}"

    async def authenticate(self, auth_data: dict) -> dict:
        code = auth_data.get("code", "")
        verifier = auth_data.get("code_verifier", "")
        token_seed = f"{self.name}:{code}:{verifier}:{secrets.token_hex(6)}"
        token_hash = hashlib.sha256(token_seed.encode()).hexdigest()
        return {
            "id": f"oauth_{self.name}",
            "provider": self.config.get("provider", self.name),
            "token_type": "Bearer",
            "access_token": f"pf_{token_hash[:32]}",
            "refresh_token": f"pf_{token_hash[32:56]}",
            "scope": self.config.get("scopes", []),
            "mode": "simulated",
            "client_id": self._client_id(),
            "client_secret_present": bool(self._client_secret()),
        }


class APIKeyConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict) -> dict:
        api_key = auth_data.get("api_key", "")
        masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) >= 8 else "***"
        return {"id": f"api_{self.name}", "token_masked": masked, "present": bool(api_key)}
