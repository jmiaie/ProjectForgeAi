from typing import Any


class ConnectorRegistry:
    _connectors: dict[str, dict[str, Any]] = {
        "google": {
            "type": "oauth",
            "provider": "google",
            "scopes": ["email", "calendar", "drive.readonly"],
        },
        "microsoft": {
            "type": "oauth",
            "provider": "microsoft",
            "mcp_support": True,
        },
        "slack": {"type": "oauth"},
        "github": {"type": "oauth"},
        "jira": {"type": "api_key"},
        "mcp_server": {"type": "mcp", "description": "Any MCP server"},
    }

    @classmethod
    def get_connector(cls, name: str):
        config = cls._connectors.get(name)
        if config is None:
            raise ValueError(f"Unknown connector: {name}")

        if config["type"] == "oauth":
            from integrations.connectors.oauth import OAuthConnector

            return OAuthConnector(name, config)
        if config["type"] == "mcp":
            from integrations.connectors.mcp import MCPConnector

            return MCPConnector(name, config)
        if config["type"] == "api_key":
            from integrations.connectors.oauth import APIKeyConnector

            return APIKeyConnector(name, config)

        raise ValueError(f"Unsupported connector type: {config['type']}")

    @classmethod
    def get_recommended(cls, compliance: str = "standard") -> list[str]:
        if compliance.lower() == "hipaa":
            return ["microsoft", "mcp_server"]
        return list(cls._connectors.keys())

    @classmethod
    def get_config(cls, name: str) -> dict[str, Any]:
        config = cls._connectors.get(name)
        if config is None:
            raise ValueError(f"Unknown connector: {name}")
        return config

    @classmethod
    def list_connectors(cls) -> dict[str, dict[str, Any]]:
        return cls._connectors.copy()
