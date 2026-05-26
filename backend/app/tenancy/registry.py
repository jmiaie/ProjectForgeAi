import json
import os
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from core.config import settings


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class TenantRecord(BaseModel):
    tenant_id: str
    name: str
    tier: str = "starter"
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TenantRegistry:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_REGISTRY_ROOT)
        os.makedirs(self.root, exist_ok=True)

    def create(self, *, name: str, tier: str | None = None, tenant_id: str | None = None) -> TenantRecord:
        record = TenantRecord(
            tenant_id=tenant_id or _generate_tenant_id(name),
            name=name.strip() or "Untitled tenant",
            tier=(tier or settings.PROJECT_TIER).lower(),
        )
        self._write(record)
        self._refresh_index()
        return record

    def get(self, tenant_id: str) -> TenantRecord | None:
        path = self.root / f"{tenant_id}.json"
        if not path.exists():
            return None
        return TenantRecord.model_validate(json.loads(path.read_text()))

    def list_tenants(self) -> list[TenantRecord]:
        self._ensure_default_tenant()
        records = []
        for path in sorted(self.root.glob("tenant_*.json")):
            records.append(TenantRecord.model_validate(json.loads(path.read_text())))
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return records

    def _ensure_default_tenant(self) -> None:
        if self.get(settings.DEFAULT_TENANT_ID) is None:
            self.create(
                name="Default Tenant",
                tier=settings.PROJECT_TIER,
                tenant_id=settings.DEFAULT_TENANT_ID,
            )

    def _write(self, record: TenantRecord) -> None:
        (self.root / f"{record.tenant_id}.json").write_text(
            json.dumps(record.as_dict(), indent=2, sort_keys=True)
        )

    def _refresh_index(self) -> None:
        index = [record.as_dict() for record in self.list_tenants()]
        (self.root / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True))


def _generate_tenant_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24]
    suffix = uuid4().hex[:8]
    return f"tenant_{slug}-{suffix}" if slug else f"tenant_{suffix}"
