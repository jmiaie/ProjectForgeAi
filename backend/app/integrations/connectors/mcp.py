import httpx

from integrations.connectors import mcp_transport


class MCPConnector:
    def __init__(self, name: str = "mcp_server", config: dict | None = None):
        self.name = name
        self.config = config or {}

    async def authenticate(self, auth_data: dict):
        transport = (auth_data.get("transport") or "http").lower()
        server_url = auth_data.get("server_url")
        token = auth_data.get("token")

        if transport == "stdio":
            command = auth_data.get("stdio_command")
            if not command:
                raise ValueError("mcp_server stdio transport requires stdio_command")
            tools = await self._discover_tools(
                transport=transport,
                stdio_command=command,
                stdio_args=auth_data.get("stdio_args"),
            )
            return {
                "id": "mcp_server",
                "transport": transport,
                "stdio_command": command,
                "stdio_args": auth_data.get("stdio_args") or [],
                "tools": tools,
                "discovery_mode": "mcp_sdk" if tools else "placeholder",
            }

        if not server_url:
            raise ValueError("mcp_server requires server_url for http/sse transport")

        tools = await self._discover_tools(
            transport=transport,
            server_url=server_url,
            token=token,
        )
        return {
            "id": "mcp_server",
            "transport": transport,
            "server_url": server_url,
            "tools": tools,
            "discovery_mode": "mcp_sdk" if transport != "http" and tools else ("http" if tools else "placeholder"),
        }

    async def discover_tools(self, connection: dict | None = None) -> dict:
        connection = connection or {}
        tools = connection.get("tools", [])
        if not tools:
            tools = await self._discover_tools(
                transport=connection.get("transport", "http"),
                server_url=connection.get("server_url"),
                token=connection.get("token"),
                stdio_command=connection.get("stdio_command"),
                stdio_args=connection.get("stdio_args"),
            )
        return {
            "connector": self.name,
            "transport": connection.get("transport", "http"),
            "server_url": connection.get("server_url"),
            "tool_count": len(tools),
            "tools": tools,
        }

    async def health(self, connection: dict | None = None) -> dict:
        connection = connection or {}
        transport = connection.get("transport", "http")
        server_url = connection.get("server_url")
        reachable = False

        if transport == "stdio":
            reachable = bool(connection.get("stdio_command"))
        elif server_url:
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
                "transport": transport,
                "server_url_present": bool(server_url),
                "stdio_command_present": bool(connection.get("stdio_command")),
                "tool_count": len(connection.get("tools", [])),
                "server_reachable": reachable,
            },
        }

    async def _discover_tools(
        self,
        *,
        transport: str = "http",
        server_url: str | None = None,
        token: str | None = None,
        stdio_command: str | None = None,
        stdio_args: list[str] | None = None,
    ) -> list[dict]:
        if transport == "sse" and server_url:
            try:
                return await mcp_transport.discover_tools_via_sse(server_url, token)
            except Exception:
                return []

        if transport == "stdio" and stdio_command:
            try:
                return await mcp_transport.discover_tools_via_stdio(stdio_command, stdio_args)
            except Exception:
                return []

        if not server_url:
            return []

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
