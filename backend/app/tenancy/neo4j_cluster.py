"""Neo4j causal cluster health checks and write-uri failover."""

from __future__ import annotations

from typing import Any

from core.config import settings


def cluster_uris() -> list[str]:
    uris: list[str] = []
    for candidate in [settings.NEO4J_URI, *(settings.NEO4J_CLUSTER_URIS or "").split(",")]:
        uri = candidate.strip()
        if uri and uri not in uris:
            uris.append(uri)
    return uris


def check_uri_health(uri: str) -> dict[str, Any]:
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            uri,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT,
        )
        driver.verify_connectivity()
        driver.close()
        return {"uri": uri, "healthy": True}
    except Exception as exc:
        return {"uri": uri, "healthy": False, "error": str(exc)}


def select_write_uri() -> str:
    if not settings.NEO4J_CLUSTER_FAILOVER_ENABLED:
        return settings.NEO4J_URI

    for uri in cluster_uris():
        if check_uri_health(uri)["healthy"]:
            return uri
    return settings.NEO4J_URI


def check_cluster_health() -> dict[str, Any]:
    members = [check_uri_health(uri) for uri in cluster_uris()]
    healthy_members = [member for member in members if member["healthy"]]
    active_write_uri = select_write_uri() if settings.NEO4J_CLUSTER_FAILOVER_ENABLED else settings.NEO4J_URI
    return {
        "failover_enabled": settings.NEO4J_CLUSTER_FAILOVER_ENABLED,
        "primary_uri": settings.NEO4J_URI,
        "active_write_uri": active_write_uri,
        "read_replica_uri": settings.NEO4J_READ_REPLICA_URI,
        "member_count": len(members),
        "healthy_count": len(healthy_members),
        "members": members,
        "status": "healthy" if healthy_members else "degraded",
    }


def connect_with_failover():
    """Return (driver, active_uri) trying cluster URIs in order when failover is enabled."""
    from neo4j import GraphDatabase

    uris = cluster_uris() if settings.NEO4J_CLUSTER_FAILOVER_ENABLED else [settings.NEO4J_URI]
    errors: list[str] = []
    for uri in uris:
        try:
            driver = GraphDatabase.driver(
                uri,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT,
            )
            driver.verify_connectivity()
            return driver, uri
        except Exception as exc:
            errors.append(f"{uri}: {exc}")
    raise RuntimeError("; ".join(errors) or "No Neo4j URIs configured")
