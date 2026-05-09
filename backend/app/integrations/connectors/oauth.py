class OAuthConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict) -> dict:
        # auth_data contains OAuth code/state from frontend
        # Implement token exchange here
        return {"id": "oauth_" + self.name, "token": auth_data.get("code")}


class APIKeyConnector:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    async def authenticate(self, auth_data: dict) -> dict:
        return {"id": f"api_{self.name}", "token": auth_data.get("api_key")}
