from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client


def _normalize_tools(tools_result) -> list[dict[str, Any]]:
    tools = getattr(tools_result, "tools", tools_result)
    if not isinstance(tools, list):
        return []
    normalized: list[dict[str, Any]] = []
    for tool in tools:
        if hasattr(tool, "model_dump"):
            normalized.append(tool.model_dump(mode="python"))
        elif isinstance(tool, dict):
            normalized.append(tool)
        else:
            normalized.append({"name": str(getattr(tool, "name", tool))})
    return normalized


async def discover_tools_via_sse(server_url: str, token: str | None = None) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with sse_client(server_url, headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return _normalize_tools(result)


async def discover_tools_via_stdio(command: str, args: list[str] | None = None) -> list[dict[str, Any]]:
    params = StdioServerParameters(command=command, args=args or [])
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return _normalize_tools(result)
