"""Multi-region tenant routing and data residency controls."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import settings
from tenancy.registry import TenantRegistry


def available_regions() -> dict[str, dict[str, str]]:
    regions: dict[str, dict[str, str]] = {}
    for item in settings.AVAILABLE_TENANT_REGIONS.split(","):
        part = item.strip()
        if not part:
            continue
        if ":" in part:
            region_id, residency = part.split(":", 1)
        else:
            region_id, residency = part, part.split("-")[0]
        regions[region_id.strip()] = {
            "region_id": region_id.strip(),
            "residency_zone": residency.strip(),
            "label": region_id.strip().replace("-", " ").title(),
        }
    return regions


class TenantRegionRegistry:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_REGISTRY_ROOT)

    def _path(self, tenant_id: str) -> Path:
        return self.root / f"{tenant_id}.region.json"

    def assign(self, tenant_id: str, region_id: str) -> dict[str, Any]:
        catalog = available_regions()
        if region_id not in catalog:
            raise ValueError(f"Unknown region: {region_id}")

        record = {
            "tenant_id": tenant_id,
            "region_id": region_id,
            "residency_zone": catalog[region_id]["residency_zone"],
            "routing_enabled": settings.TENANT_REGION_ROUTING_ENABLED,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        os.makedirs(self.root, exist_ok=True)
        self._path(tenant_id).write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def get(self, tenant_id: str) -> dict[str, Any]:
        path = self._path(tenant_id)
        if path.exists():
            return json.loads(path.read_text())

        default_region = settings.DEFAULT_TENANT_REGION
        catalog = available_regions()
        residency = catalog.get(default_region, {}).get("residency_zone", "us")
        return {
            "tenant_id": tenant_id,
            "region_id": default_region,
            "residency_zone": residency,
            "routing_enabled": settings.TENANT_REGION_ROUTING_ENABLED,
            "configured": False,
        }

    def validate_request(self, tenant_id: str, request_region: str | None) -> dict[str, Any]:
        assigned = self.get(tenant_id)
        if not settings.TENANT_REGION_ROUTING_ENABLED or not request_region:
            return {"allowed": True, "tenant_region": assigned, "request_region": request_region}

        allowed = request_region == assigned["region_id"]
        return {
            "allowed": allowed,
            "tenant_region": assigned,
            "request_region": request_region,
            "reason": "Region matches tenant assignment" if allowed else "Request region does not match tenant data residency",
        }


def ensure_tenant_region(tenant_id: str, region_id: str | None = None) -> dict[str, Any]:
    registry = TenantRegionRegistry()
    region = region_id or settings.DEFAULT_TENANT_REGION
    return registry.assign(tenant_id, region)


def list_region_catalog() -> dict[str, Any]:
    from tenancy.migration import region_read_replica_map

    return {
        "default_region": settings.DEFAULT_TENANT_REGION,
        "routing_enabled": settings.TENANT_REGION_ROUTING_ENABLED,
        "read_replicas_enabled": settings.TENANT_REGION_READ_REPLICAS_ENABLED,
        "read_replica_uris": region_read_replica_map(),
        "regions": list(available_regions().values()),
    }
