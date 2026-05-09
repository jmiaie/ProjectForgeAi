class ConnectorRegistry:
    _connectors = {
        "google": {
            "type": "oauth",
            "provider": "google",
            "scopes": ["email", "calendar", "drive.readonly"],
        },
        "microsoft": {"type": "oauth", "provider": "microsoft", "mcp_support": True},
        "slack": {"type": "oauth"},
        "github": {"type": "oauth"},
        "jira": {"type": "api_key"},
        "mcp_server": {"type": "mcp", "description": "Any MCP server"},
    }

    @classmethod
    def get_connector(cls, name: str):
        config = cls._connectors.get(name)
        if not config:
            raise ValueError(f"Unknown connector: {name}")

        if config["type"] == "oauth":
            from app.integrations.connectors.oauth import OAuthConnector

            return OAuthConnector(name, config)
        if config["type"] == "mcp":
            from app.integrations.connectors.mcp import MCPConnector

            return MCPConnector()
        if config["type"] == "api_key":
            from app.integrations.connectors.oauth import APIKeyConnector

            return APIKeyConnector(name, config)
        raise ValueError(f"Unknown connector type for {name}: {config['type']}")

    @classmethod
    def get_recommended(cls, compliance: str = "standard") -> list[str]:
        # Compliance-sensitive filtering can be added here later.
        return list(cls._connectors.keys())
