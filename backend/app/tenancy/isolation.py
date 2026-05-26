from pathlib import Path

from tenancy.context import tenant_scoped_root


class TenantIsolation:
    @staticmethod
    def project_registry_root(tenant_id: str) -> str:
        from core.config import settings

        return tenant_scoped_root(settings.PROJECT_REGISTRY_ROOT, tenant_id)

    @staticmethod
    def rbac_root(tenant_id: str) -> str:
        from core.config import settings

        return tenant_scoped_root(settings.RBAC_MEMBERSHIP_ROOT, tenant_id)

    @staticmethod
    def ingestion_root(tenant_id: str) -> str:
        from core.config import settings

        return tenant_scoped_root(settings.INGESTION_MANIFEST_ROOT, tenant_id)

    @staticmethod
    def ensure_tenant_dirs(tenant_id: str) -> None:
        from core.config import settings

        if not settings.TENANT_ISOLATION_ENABLED:
            return
        for base in (
            settings.PROJECT_REGISTRY_ROOT,
            settings.RBAC_MEMBERSHIP_ROOT,
            settings.INGESTION_MANIFEST_ROOT,
            settings.COMPLIANCE_PROFILE_ROOT,
            settings.ORCHESTRATION_RUN_ROOT,
        ):
            Path(tenant_scoped_root(base, tenant_id)).mkdir(parents=True, exist_ok=True)
