from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Header

from core.config import settings
from tenancy.registry import TenantRegistry


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    name: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"tenant_id": self.tenant_id, "name": self.name}


def get_tenant_registry() -> TenantRegistry:
    return TenantRegistry()


def get_tenant_context(
    x_projectforge_tenant: Annotated[str | None, Header()] = None,
    registry: TenantRegistry = Depends(get_tenant_registry),
) -> TenantContext:
    tenant_id = x_projectforge_tenant or settings.DEFAULT_TENANT_ID
    record = registry.get(tenant_id)
    if record is None and settings.TENANT_ISOLATION_ENABLED:
        registry._ensure_default_tenant()
        record = registry.get(settings.DEFAULT_TENANT_ID)
        tenant_id = settings.DEFAULT_TENANT_ID
    return TenantContext(tenant_id=tenant_id, name=record.name if record else None)


def tenant_scoped_root(base_root: str, tenant_id: str) -> str:
    if not settings.TENANT_ISOLATION_ENABLED:
        return base_root
    return str(Path(base_root) / tenant_id)
