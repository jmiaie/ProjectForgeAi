class MCPConnector:
    async def authenticate(self, auth_data: dict):
        server_url = auth_data.get("server_url")
        if not server_url:
            raise ValueError("mcp_server requires server_url")

        try:
            import mcp
        except ImportError:
            return {
                "id": "mcp_server",
                "server_url": server_url,
                "tools": [],
                "warning": "MCP SDK is not installed; connected in placeholder mode.",
            }

        client = mcp.Client(server_url=server_url, auth_token=auth_data.get("token"))
        tools = await client.list_tools()
        return {"id": "mcp_server", "client": client, "tools": tools}
