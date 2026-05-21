"""Model Context Protocol (MCP) connector.

When the official ``mcp`` SDK is installed we use it to discover the remote
server's tools. Otherwise the connector returns a deterministic stub so the
intake wizard remains exercisable in development.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - optional dependency at scaffold stage
    import mcp  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    mcp = None  # type: ignore[assignment]


class MCPConnector:
    async def authenticate(self, auth_data: dict[str, Any]) -> dict[str, Any]:
        server_url = auth_data.get("server_url")
        if not server_url:
            raise ValueError("server_url is required to connect to an MCP server")

        if mcp is None:
            return {
                "id": f"mcp_{server_url}",
                "server_url": server_url,
                "tools": [],
                "stub": True,
            }

        client = mcp.Client(  # type: ignore[union-attr]
            server_url=server_url, auth_token=auth_data.get("token")
        )
        tools = await client.list_tools()
        return {
            "id": f"mcp_{server_url}",
            "server_url": server_url,
            "tools": tools,
        }
