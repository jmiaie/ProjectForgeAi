"""Tenant data export and import for cross-region migrations."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.config import settings
from tenancy.billing import TenantBillingService
from tenancy.migration import TenantMigrationService
from tenancy.neo4j_isolation import TenantNeo4jRegistry
from tenancy.regions import TenantRegionRegistry
from tenancy.registry import TenantRegistry


class TenantDataPortabilityService:
    def __init__(self, export_root: str | None = None):
        self.export_root = Path(export_root or settings.TENANT_EXPORT_ROOT)
        self.registry = TenantRegistry()

    def _export_path(self, tenant_id: str, export_id: str) -> Path:
        path = self.export_root / tenant_id / f"{export_id}.json"
        os.makedirs(path.parent, exist_ok=True)
        return path

    def export_tenant_data(self, tenant_id: str) -> dict[str, Any]:
        tenant = self.registry.get(tenant_id)
        if tenant is None:
            raise ValueError(f"Unknown tenant: {tenant_id}")

        from tenancy.stripe_billing import SubscriptionStore
        from tenancy.usage_metering import UsageMeteringService

        export_id = f"export_{uuid4().hex}"
        bundle = {
            "export_id": export_id,
            "tenant_id": tenant_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "tenant": tenant.as_dict(),
            "region": TenantRegionRegistry().get(tenant_id),
            "neo4j": TenantNeo4jRegistry().status(tenant_id),
            "billing": {
                "quota": TenantBillingService().quota_status(tenant_id),
                "subscription": SubscriptionStore().get(tenant_id),
                "usage_reports": UsageMeteringService().list_reports(tenant_id),
            },
            "migrations": TenantMigrationService().migration_status(tenant_id),
        }
        path = self._export_path(tenant_id, export_id)
        path.write_text(json.dumps(bundle, indent=2, sort_keys=True))
        return {"status": "exported", "export_id": export_id, "path": str(path), "bundle": bundle}

    def import_tenant_data(self, tenant_id: str, *, export_id: str | None = None, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        if bundle is None:
            if not export_id:
                raise ValueError("export_id or bundle required")
            path = self._export_path(tenant_id, export_id)
            if not path.exists():
                raise ValueError(f"Export not found: {export_id}")
            bundle = json.loads(path.read_text())

        if bundle.get("tenant_id") != tenant_id:
            raise ValueError("Bundle tenant_id does not match target tenant")

        region_id = bundle.get("region", {}).get("region_id")
        if region_id:
            TenantRegionRegistry().assign(tenant_id, region_id)

        TenantNeo4jRegistry().ensure_database(tenant_id)
        import_record = {
            "import_id": f"import_{uuid4().hex}",
            "tenant_id": tenant_id,
            "export_id": bundle.get("export_id"),
            "imported_at": datetime.now(UTC).isoformat(),
            "status": "completed",
        }
        TenantMigrationService().store.append(
            tenant_id,
            {
                "migration_id": import_record["import_id"],
                "tenant_id": tenant_id,
                "from_region": bundle.get("region", {}).get("region_id"),
                "to_region": region_id,
                "status": "imported",
                "completed_at": import_record["imported_at"],
            },
        )
        return {"status": "imported", "tenant_id": tenant_id, "import": import_record, "region_id": region_id}

    def list_exports(self, tenant_id: str) -> dict[str, Any]:
        tenant_dir = self.export_root / tenant_id
        if not tenant_dir.exists():
            return {"tenant_id": tenant_id, "exports": []}
        exports = []
        for path in sorted(tenant_dir.glob("export_*.json")):
            payload = json.loads(path.read_text())
            exports.append(
                {
                    "export_id": payload.get("export_id", path.stem),
                    "exported_at": payload.get("exported_at"),
                    "path": str(path),
                }
            )
        return {"tenant_id": tenant_id, "exports": exports}
