"""Cross-region read replicas and tenant migration tooling."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import settings


def region_read_replica_map() -> dict[str, str]:
    replicas: dict[str, str] = {}
    for item in settings.REGION_READ_REPLICA_URIS.split(","):
        part = item.strip()
        if not part or ":" not in part:
            continue
        region_id, uri = part.split(":", 1)
        replicas[region_id.strip()] = uri.strip()
    return replicas


def resolve_region_read_uri(region_id: str) -> str | None:
    if not settings.TENANT_REGION_READ_REPLICAS_ENABLED:
        return None
    return region_read_replica_map().get(region_id)


def resolve_tenant_read_uri(tenant_id: str) -> str | None:
    from tenancy.regions import TenantRegionRegistry

    region = TenantRegionRegistry().get(tenant_id)
    regional = resolve_region_read_uri(region["region_id"])
    if regional:
        return regional

    if settings.NEO4J_READ_REPLICA_ENABLED and settings.NEO4J_READ_REPLICA_URI:
        from tenancy.neo4j_isolation import tenant_uses_read_replica

        if tenant_uses_read_replica(tenant_id):
            return settings.NEO4J_READ_REPLICA_URI
    return None


class TenantMigrationStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_REGISTRY_ROOT)

    def _path(self, tenant_id: str) -> Path:
        return self.root / f"{tenant_id}.migrations.json"

    def append(self, tenant_id: str, record: dict[str, Any]) -> dict[str, Any]:
        path = self._path(tenant_id)
        os.makedirs(self.root, exist_ok=True)
        records = json.loads(path.read_text()) if path.exists() else []
        records.append(record)
        path.write_text(json.dumps(records, indent=2, sort_keys=True))
        return record

    def list_migrations(self, tenant_id: str) -> list[dict[str, Any]]:
        path = self._path(tenant_id)
        if not path.exists():
            return []
        return json.loads(path.read_text())


class TenantMigrationService:
    def __init__(self):
        self.store = TenantMigrationStore()

    def migrate_region(self, tenant_id: str, target_region: str) -> dict[str, Any]:
        from tenancy.neo4j_isolation import TenantNeo4jRegistry
        from tenancy.regions import TenantRegionRegistry, available_regions

        catalog = available_regions()
        if target_region not in catalog:
            raise ValueError(f"Unknown region: {target_region}")

        region_registry = TenantRegionRegistry()
        current = region_registry.get(tenant_id)
        if current["region_id"] == target_region:
            return {"status": "noop", "tenant_id": tenant_id, "region_id": target_region}

        record = region_registry.assign(tenant_id, target_region)
        neo4j_status = TenantNeo4jRegistry().ensure_database(tenant_id)
        read_uri = resolve_tenant_read_uri(tenant_id)
        migration = {
            "migration_id": f"mig_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            "tenant_id": tenant_id,
            "from_region": current["region_id"],
            "to_region": target_region,
            "read_replica_uri": read_uri,
            "residency_zone": catalog[target_region]["residency_zone"],
            "status": "completed",
            "completed_at": datetime.now(UTC).isoformat(),
        }
        self.store.append(tenant_id, migration)
        return {
            "status": "migrated",
            "tenant_id": tenant_id,
            "region": record,
            "neo4j": neo4j_status,
            "read_replica_uri": read_uri,
            "migration": migration,
        }

    def migration_status(self, tenant_id: str) -> dict[str, Any]:
        from tenancy.regions import TenantRegionRegistry

        return {
            "tenant_id": tenant_id,
            "region": TenantRegionRegistry().get(tenant_id),
            "read_replica_uri": resolve_tenant_read_uri(tenant_id),
            "migrations": self.store.list_migrations(tenant_id),
            "available_replicas": region_read_replica_map(),
        }
