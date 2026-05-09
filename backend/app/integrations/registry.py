class ConnectorRegistry:
    _connectors = {
        "google": {
            "type": "oauth",
            "provider": "google",
            "scopes": ["email", "calendar", "drive.readonly"],
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "client_id_env": "GOOGLE_CLIENT_ID",
            "client_secret_env": "GOOGLE_CLIENT_SECRET",
        },
        "microsoft": {
            "type": "oauth",
            "provider": "microsoft",
            "mcp_support": True,
            "scopes": ["openid", "profile", "email", "offline_access"],
            "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "client_id_env": "MICROSOFT_CLIENT_ID",
            "client_secret_env": "MICROSOFT_CLIENT_SECRET",
        },
        "slack": {
            "type": "oauth",
            "provider": "slack",
            "scopes": ["channels:read", "chat:write", "users:read"],
            "authorization_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "client_id_env": "SLACK_CLIENT_ID",
            "client_secret_env": "SLACK_CLIENT_SECRET",
        },
        "github": {
            "type": "oauth",
            "provider": "github",
            "scopes": ["repo", "read:user", "read:org"],
            "authorization_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "client_id_env": "GITHUB_CLIENT_ID",
            "client_secret_env": "GITHUB_CLIENT_SECRET",
        },
        "jira": {"type": "api_key", "provider": "jira"},
        "mcp_server": {"type": "mcp", "description": "Any MCP server"},
    }

    @classmethod
    def get_config(cls, name: str) -> dict:
        config = cls._connectors.get(name)
        if not config:
            raise ValueError(f"Unknown connector: {name}")
        return config

    @classmethod
    def get_type(cls, name: str) -> str:
        return cls.get_config(name)["type"]

    @classmethod
    def get_connector(cls, name: str):
        config = cls.get_config(name)

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

    @classmethod
    def get_recommended_with_metadata(cls, compliance: str = "standard") -> list[dict]:
        connectors = []
        for connector_name in cls.get_recommended(compliance):
            config = cls.get_config(connector_name)
            connectors.append(
                {
                    "name": connector_name,
                    "type": config.get("type", "unknown"),
                    "provider": config.get("provider", connector_name),
                    "scopes": config.get("scopes", []),
                    "mcp_support": bool(config.get("mcp_support", False)),
                    "description": config.get("description"),
                }
            )
        return connectors
