class MCPConnector:
    async def authenticate(self, auth_data: dict) -> dict:
        server_url = auth_data["server_url"]
        token = auth_data.get("token")

        try:
            import mcp
        except ImportError:
            # Keep bootstrapping functional even when MCP SDK is not installed yet.
            return {"client": None, "tools": [], "server_url": server_url, "token_present": bool(token)}

        client = mcp.Client(server_url=server_url, auth_token=token)
        tools = await client.list_tools()
        return {"client": client, "tools": tools}
