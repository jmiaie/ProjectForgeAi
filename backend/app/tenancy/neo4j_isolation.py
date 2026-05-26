import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.config import settings


def tenant_database_name(tenant_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", tenant_id.lower())[:32]
    return f"pf{slug or 'default'}"


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
        record = {
            "tenant_id": tenant_id,
            "database": database,
            "isolation_mode": "database" if settings.NEO4J_TENANT_ISOLATION_ENABLED else "disabled",
            "updated_at": datetime.now(UTC).isoformat(),
        }
        os.makedirs(self.root, exist_ok=True)
        self._path(tenant_id).write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def status(self, tenant_id: str) -> dict[str, Any]:
        path = self._path(tenant_id)
        if not path.exists():
            return {
                "tenant_id": tenant_id,
                "configured": False,
                "database": tenant_database_name(tenant_id),
                "isolation_enabled": settings.NEO4J_TENANT_ISOLATION_ENABLED,
            }
        payload = json.loads(path.read_text())
        payload["configured"] = True
        payload["isolation_enabled"] = settings.NEO4J_TENANT_ISOLATION_ENABLED
        return payload


def create_graph_adapter(tenant_id: str | None = None):
    from graph.adapter import Neo4jGraphAdapter

    database = None
    if settings.NEO4J_TENANT_ISOLATION_ENABLED and tenant_id:
        registry = TenantNeo4jRegistry()
        registry.ensure_database(tenant_id)
        database = registry.get_database(tenant_id)
    return Neo4jGraphAdapter(tenant_id=tenant_id, database=database)
