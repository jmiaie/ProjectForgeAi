import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import settings
from core.usage_meter import LLMUsageMeter
from projects.registry import ProjectRegistry
from tenancy.registry import TenantRegistry


TIER_QUOTAS: dict[str, dict[str, int | None]] = {
    "starter": {
        "max_projects": 5,
        "max_api_requests": 10_000,
        "max_llm_tokens": 100_000,
        "max_orchestrator_runs": 50,
    },
    "pro": {
        "max_projects": 25,
        "max_api_requests": 100_000,
        "max_llm_tokens": 1_000_000,
        "max_orchestrator_runs": 500,
    },
    "enterprise": {
        "max_projects": None,
        "max_api_requests": None,
        "max_llm_tokens": None,
        "max_orchestrator_runs": None,
    },
}


class TenantUsageStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_USAGE_ROOT)

    def _path(self, tenant_id: str) -> Path:
        path = self.root / tenant_id / "usage.json"
        os.makedirs(path.parent, exist_ok=True)
        return path

    def _load(self, tenant_id: str) -> dict[str, Any]:
        path = self._path(tenant_id)
        if not path.exists():
            return {
                "tenant_id": tenant_id,
                "api_requests": 0,
                "llm_tokens": 0,
                "orchestrator_runs": 0,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        return json.loads(path.read_text())

    def _save(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["updated_at"] = datetime.now(UTC).isoformat()
        self._path(payload["tenant_id"]).write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload

    def record_api_request(self, tenant_id: str, count: int = 1) -> dict[str, Any]:
        payload = self._load(tenant_id)
        payload["api_requests"] = int(payload.get("api_requests", 0)) + count
        return self._save(payload)

    def record_llm_tokens(self, tenant_id: str, tokens: int) -> dict[str, Any]:
        payload = self._load(tenant_id)
        payload["llm_tokens"] = int(payload.get("llm_tokens", 0)) + tokens
        return self._save(payload)

    def record_orchestrator_run(self, tenant_id: str) -> dict[str, Any]:
        payload = self._load(tenant_id)
        payload["orchestrator_runs"] = int(payload.get("orchestrator_runs", 0)) + 1
        return self._save(payload)

    def snapshot(self, tenant_id: str) -> dict[str, Any]:
        return self._load(tenant_id)


class TenantBillingService:
    def __init__(
        self,
        tenant_registry: TenantRegistry | None = None,
        project_registry_factory=None,
        usage_store: TenantUsageStore | None = None,
        llm_usage_meter: LLMUsageMeter | None = None,
    ):
        self.tenant_registry = tenant_registry or TenantRegistry()
        self.usage_store = usage_store or TenantUsageStore()
        self.llm_usage_meter = llm_usage_meter or LLMUsageMeter()
        self.project_registry_factory = project_registry_factory or (
            lambda tenant_id: ProjectRegistry(tenant_id=tenant_id)
        )

    def quotas_for_tenant(self, tenant_id: str) -> dict[str, int | None]:
        tenant = self.tenant_registry.get(tenant_id)
        tier = tenant.tier if tenant else settings.PROJECT_TIER
        return dict(TIER_QUOTAS.get(tier.lower(), TIER_QUOTAS["starter"]))

    def usage_summary(self, tenant_id: str) -> dict[str, Any]:
        tenant = self.tenant_registry.get(tenant_id)
        if tenant is None:
            if tenant_id == settings.DEFAULT_TENANT_ID:
                self.tenant_registry._ensure_default_tenant()
                tenant = self.tenant_registry.get(tenant_id)
            if tenant is None:
                raise ValueError(f"Unknown tenant: {tenant_id}")

        store_usage = self.usage_store.snapshot(tenant_id)
        projects = self.project_registry_factory(tenant_id).list_projects(include_archived=True)
        llm_tokens = 0
        llm_calls = 0
        for project in projects:
            summary = self.llm_usage_meter.summary(project.project_id)
            llm_tokens += int(summary.get("total_tokens", 0))
            llm_calls += int(summary.get("call_count", 0))

        return {
            "tenant_id": tenant_id,
            "tier": tenant.tier,
            "projects": len(projects),
            "api_requests": store_usage.get("api_requests", 0),
            "llm_tokens": max(int(store_usage.get("llm_tokens", 0)), llm_tokens),
            "llm_calls": llm_calls,
            "orchestrator_runs": store_usage.get("orchestrator_runs", 0),
            "updated_at": store_usage.get("updated_at"),
        }

    def quota_status(self, tenant_id: str) -> dict[str, Any]:
        usage = self.usage_summary(tenant_id)
        quotas = self.quotas_for_tenant(tenant_id)
        checks = {}
        for key, limit in quotas.items():
            metric_key = key.replace("max_", "")
            current = usage.get(metric_key, 0)
            if limit is None:
                checks[key] = {"current": current, "limit": None, "remaining": None, "allowed": True}
            else:
                remaining = max(limit - current, 0)
                checks[key] = {
                    "current": current,
                    "limit": limit,
                    "remaining": remaining,
                    "allowed": current < limit,
                }
        return {"tenant_id": tenant_id, "tier": usage["tier"], "usage": usage, "quotas": quotas, "checks": checks}

    def check_action(self, tenant_id: str, action: str) -> dict[str, Any]:
        status = self.quota_status(tenant_id)
        mapping = {
            "api_request": "max_api_requests",
            "llm_call": "max_llm_tokens",
            "project_create": "max_projects",
            "orchestrator_run": "max_orchestrator_runs",
        }
        quota_key = mapping.get(action)
        if quota_key is None:
            return {"allowed": True, "action": action, "reason": "Unknown action — allowed by default"}
        check = status["checks"][quota_key]
        allowed = check["allowed"]
        reason = "Within tenant quota" if allowed else f"Tenant quota exceeded for {quota_key}"
        return {"allowed": allowed, "action": action, "reason": reason, "quota": check}

    def record_event(self, tenant_id: str, event_type: str, amount: int = 1) -> dict[str, Any]:
        if event_type == "api_request":
            return self.usage_store.record_api_request(tenant_id, amount)
        if event_type == "llm_tokens":
            return self.usage_store.record_llm_tokens(tenant_id, amount)
        if event_type == "orchestrator_run":
            return self.usage_store.record_orchestrator_run(tenant_id)
        raise ValueError(f"Unknown billing event: {event_type}")
