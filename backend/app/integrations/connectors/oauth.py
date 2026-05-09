class OAuthConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict):
        return {
            "id": f"oauth_{self.name}",
            "provider": self.config.get("provider", self.name),
            "token": auth_data.get("code"),
            "scopes": self.config.get("scopes", []),
        }


class APIKeyConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict):
        api_key = auth_data.get("api_key")
        if not api_key:
            raise ValueError(f"{self.name} requires api_key")
        return {"id": f"api_key_{self.name}", "has_key": True}
