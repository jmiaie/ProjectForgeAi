"""API-key based connector (Jira, custom REST APIs, etc.)."""

from __future__ import annotations

from typing import Any


class ApiKeyConnector:
    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict[str, Any]) -> dict[str, Any]:
        api_key = auth_data.get("api_key")
        if not api_key:
            raise ValueError("api_key is required for API key connectors")
        return {
            "id": f"apikey_{self.name}",
            "provider": self.config.get("provider", self.name),
            "base_url": auth_data.get("base_url"),
            "stored": True,
        }
