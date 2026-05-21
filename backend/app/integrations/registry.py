"""Registry of supported integration connectors.

The registry is the single source of truth for connector metadata used by the
intake wizard and the integrations manager. Each entry describes the auth
mechanism, recommended scopes, and any MCP support hints.
"""

from __future__ import annotations

from typing import Any


class ConnectorRegistry:
    """Static registry of known connectors."""

    _connectors: dict[str, dict[str, Any]] = {
        "google": {
            "type": "oauth",
            "provider": "google",
            "scopes": ["email", "calendar", "drive.readonly"],
            "compliance_tiers": ["standard", "soc2", "gdpr"],
        },
        "microsoft": {
            "type": "oauth",
            "provider": "microsoft",
            "scopes": ["Mail.Read", "Calendars.Read", "Files.Read"],
            "mcp_support": True,
            "compliance_tiers": ["standard", "soc2", "hipaa"],
        },
        "slack": {
            "type": "oauth",
            "provider": "slack",
            "scopes": ["channels:read", "chat:write"],
            "compliance_tiers": ["standard"],
        },
        "github": {
            "type": "oauth",
            "provider": "github",
            "scopes": ["repo", "read:org"],
            "compliance_tiers": ["standard", "soc2"],
        },
        "jira": {
            "type": "api_key",
            "provider": "atlassian",
            "compliance_tiers": ["standard", "soc2"],
        },
        "mcp_server": {
            "type": "mcp",
            "description": "Any MCP-compatible server (tool discovery via list_tools)",
            "compliance_tiers": ["standard", "soc2", "hipaa", "legal"],
        },
    }

    @classmethod
    def list_all(cls) -> list[dict[str, Any]]:
        return [{"name": name, **config} for name, config in cls._connectors.items()]

    @classmethod
    def get_metadata(cls, name: str) -> dict[str, Any]:
        config = cls._connectors.get(name)
        if config is None:
            raise ValueError(f"Unknown connector: {name}")
        return {"name": name, **config}

    @classmethod
    def get_connector(cls, name: str) -> Any:
        config = cls._connectors.get(name)
        if config is None:
            raise ValueError(f"Unknown connector: {name}")

        connector_type = config["type"]
        if connector_type == "oauth":
            from app.integrations.connectors.oauth import OAuthConnector

            return OAuthConnector(name, config)
        if connector_type == "api_key":
            from app.integrations.connectors.api_key import ApiKeyConnector

            return ApiKeyConnector(name, config)
        if connector_type == "mcp":
            from app.integrations.connectors.mcp import MCPConnector

            return MCPConnector()
        raise ValueError(f"Unsupported connector type: {connector_type}")

    @classmethod
    def get_recommended(cls, compliance: str = "standard") -> list[dict[str, Any]]:
        recommended: list[dict[str, Any]] = []
        for name, config in cls._connectors.items():
            tiers = config.get("compliance_tiers", ["standard"])
            if compliance in tiers:
                recommended.append({"name": name, **config})
        return recommended
