import httpx


class MCPConnector:
    def __init__(self, name: str = "mcp_server", config: dict | None = None):
        self.name = name
        self.config = config or {}

    async def authenticate(self, auth_data: dict):
        server_url = auth_data.get("server_url")
        if not server_url:
            raise ValueError("mcp_server requires server_url")

        tools = await self._discover_tools(server_url, auth_data.get("token"))
        return {
            "id": "mcp_server",
            "server_url": server_url,
            "tools": tools,
            "discovery_mode": "http" if tools else "placeholder",
        }

    async def discover_tools(self, connection: dict | None = None) -> dict:
        server_url = connection.get("server_url") if connection else None
        tools = connection.get("tools", []) if connection else []
        if server_url and not tools:
            tools = await self._discover_tools(server_url, connection.get("token") if connection else None)
        return {
            "connector": self.name,
            "server_url": server_url,
            "tool_count": len(tools),
            "tools": tools,
        }

    async def health(self, connection: dict | None = None) -> dict:
        server_url = connection.get("server_url") if connection else None
        reachable = False
        if server_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(server_url)
                    reachable = response.status_code < 500
            except httpx.HTTPError:
                reachable = False
        return {
            "connector": self.name,
            "status": "connected" if connection else "not_connected",
            "checks": {
                "server_url_present": bool(server_url),
                "tool_count": len(connection.get("tools", [])) if connection else 0,
                "server_reachable": reachable,
            },
        }

    async def _discover_tools(self, server_url: str, token: str | None = None) -> list[dict]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        candidates = [
            server_url.rstrip("/") + "/tools",
            server_url.rstrip("/") + "/mcp/tools",
            server_url.rstrip("/") + "/.well-known/mcp/tools",
        ]
        async with httpx.AsyncClient(timeout=8.0) as client:
            for url in candidates:
                try:
                    response = await client.get(url, headers=headers)
                    if response.status_code >= 400:
                        continue
                    payload = response.json()
                    tools = payload.get("tools") if isinstance(payload, dict) else payload
                    if isinstance(tools, list):
                        return [
                            tool if isinstance(tool, dict) else {"name": str(tool)}
                            for tool in tools
                        ]
                except (httpx.HTTPError, ValueError):
                    continue
        return []
