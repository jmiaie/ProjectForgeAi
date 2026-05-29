import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import settings


def tenant_database_name(tenant_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", tenant_id.lower())[:32]
    return f"pf{slug or 'default'}"


def read_replica_tiers() -> set[str]:
    return {tier.strip().lower() for tier in settings.NEO4J_READ_REPLICA_TIERS.split(",") if tier.strip()}


def tenant_uses_read_replica(tenant_id: str) -> bool:
    if not settings.NEO4J_READ_REPLICA_ENABLED or not settings.NEO4J_READ_REPLICA_URI:
        return False
    from tenancy.registry import TenantRegistry

    tenant = TenantRegistry().get(tenant_id)
    if tenant is None:
        return False
    return tenant.tier.lower() in read_replica_tiers()


def resolve_read_uri(tenant_id: str | None) -> str | None:
    if tenant_id:
        from tenancy.migration import resolve_tenant_read_uri

        regional = resolve_tenant_read_uri(tenant_id)
        if regional:
            return regional
    if tenant_id and tenant_uses_read_replica(tenant_id):
        return settings.NEO4J_READ_REPLICA_URI
    return None


def provision_tenant_database(database: str) -> dict[str, Any]:
    if not settings.NEO4J_AUTO_PROVISION_DATABASES:
        return {"provisioned": False, "database": database, "reason": "auto_provision_disabled"}

    try:
        from neo4j import GraphDatabase

        from graph.bootstrap import bootstrap_neo4j

        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT,
        )
        driver.verify_connectivity()

        with driver.session(database="system") as session:
            session.run(f"CREATE DATABASE `{database}` IF NOT EXISTS WAIT")

        bootstrap_result = bootstrap_neo4j(driver, database=database)
        driver.close()
        return {
            "provisioned": True,
            "database": database,
            "bootstrap": bootstrap_result,
        }
    except Exception as exc:
        return {
            "provisioned": False,
            "database": database,
            "error": str(exc),
        }


class TenantNeo4jRegistry:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_REGISTRY_ROOT)

    def _path(self, tenant_id: str) -> Path:
        return self.root / f"{tenant_id}.neo4j.json"

    def get_database(self, tenant_id: str) -> str:
        path = self._path(tenant_id)
        if path.exists():
            return json.loads(path.read_text()).get("database", tenant_database_name(tenant_id))
        return tenant_database_name(tenant_id)

    def ensure_database(self, tenant_id: str) -> dict[str, Any]:
        database = tenant_database_name(tenant_id)
        provision_result: dict[str, Any] | None = None
        if settings.NEO4J_TENANT_ISOLATION_ENABLED and settings.NEO4J_AUTO_PROVISION_DATABASES:
            provision_result = provision_tenant_database(database)

        read_replica = tenant_uses_read_replica(tenant_id)
        record = {
            "tenant_id": tenant_id,
            "database": database,
            "isolation_mode": "database" if settings.NEO4J_TENANT_ISOLATION_ENABLED else "disabled",
            "auto_provision_enabled": settings.NEO4J_AUTO_PROVISION_DATABASES,
            "read_replica_enabled": read_replica,
            "read_replica_uri": settings.NEO4J_READ_REPLICA_URI if read_replica else None,
            "provisioned": provision_result.get("provisioned") if provision_result else False,
            "provision_error": provision_result.get("error") if provision_result else None,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        os.makedirs(self.root, exist_ok=True)
        self._path(tenant_id).write_text(json.dumps(record, indent=2, sort_keys=True))
        if provision_result:
            record["provision"] = provision_result
        return record

    def status(self, tenant_id: str) -> dict[str, Any]:
        path = self._path(tenant_id)
        if not path.exists():
            return {
                "tenant_id": tenant_id,
                "configured": False,
                "database": tenant_database_name(tenant_id),
                "isolation_enabled": settings.NEO4J_TENANT_ISOLATION_ENABLED,
                "auto_provision_enabled": settings.NEO4J_AUTO_PROVISION_DATABASES,
                "read_replica_enabled": tenant_uses_read_replica(tenant_id),
                "read_replica_uri": resolve_read_uri(tenant_id),
            }
        payload = json.loads(path.read_text())
        payload["configured"] = True
        payload["isolation_enabled"] = settings.NEO4J_TENANT_ISOLATION_ENABLED
        payload["auto_provision_enabled"] = settings.NEO4J_AUTO_PROVISION_DATABASES
        payload["read_replica_enabled"] = tenant_uses_read_replica(tenant_id)
        payload["read_replica_uri"] = resolve_read_uri(tenant_id)
        return payload


def create_graph_adapter(tenant_id: str | None = None):
    from graph.adapter import Neo4jGraphAdapter

    database = None
    read_uri = resolve_read_uri(tenant_id)
    if settings.NEO4J_TENANT_ISOLATION_ENABLED and tenant_id:
        registry = TenantNeo4jRegistry()
        registry.ensure_database(tenant_id)
        database = registry.get_database(tenant_id)
    return Neo4jGraphAdapter(tenant_id=tenant_id, database=database, read_uri=read_uri)
