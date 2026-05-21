"""Graph backend health probes for /health and ops."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings


async def graph_backend_status() -> dict[str, Any]:
    """Report configured graph backend and Neo4j reachability."""

    settings = get_settings()
    backend = settings.GRAPH_BACKEND.lower()
    status: dict[str, Any] = {
        "configured": backend,
        "active": backend,
    }

    if backend == "neo4j":
        try:
            from neo4j import AsyncGraphDatabase  # type: ignore[import-not-found]

            driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                status["neo4j"] = "connected" if record and record["ok"] == 1 else "degraded"
            await driver.close()
        except Exception as exc:  # pragma: no cover
            status["neo4j"] = "unavailable"
            status["active"] = "memory"
            status["fallback_reason"] = str(exc)
    else:
        status["neo4j"] = "not_configured"

    return status
