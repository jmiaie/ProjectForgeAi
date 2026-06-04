"""Scheduled overage reporting and invoice automation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.config import settings
from tenancy.registry import TenantRegistry
from tenancy.usage_metering import UsageMeteringService


class BillingSchedulerService:
    def __init__(self, metering: UsageMeteringService | None = None):
        self.metering = metering or UsageMeteringService()
        self.registry = TenantRegistry()

    async def run_scheduled_billing(self, tenant_id: str | None = None) -> dict[str, Any]:
        if not settings.BILLING_OVERAGE_SCHEDULER_ENABLED:
            return {"status": "disabled", "processed": 0, "results": []}

        tenants = self.registry.list_tenants()
        if tenant_id:
            tenants = [tenant for tenant in tenants if tenant.tenant_id == tenant_id]
            if not tenants:
                raise ValueError(f"Unknown tenant: {tenant_id}")

        results: list[dict[str, Any]] = []
        for tenant in tenants:
            summary = self.metering.overage_summary(tenant.tenant_id)
            if summary["overage_tokens"] <= 0:
                results.append(
                    {
                        "tenant_id": tenant.tenant_id,
                        "status": "skipped",
                        "reason": "no_overage",
                    }
                )
                continue

            report_result = await self.metering.report_llm_overage(tenant.tenant_id)
            entry: dict[str, Any] = {
                "tenant_id": tenant.tenant_id,
                "report": report_result,
            }
            if settings.BILLING_OVERAGE_AUTO_INVOICE and report_result.get("status") == "reported":
                try:
                    invoice_result = await self.metering.create_overage_invoice(tenant.tenant_id)
                    entry["invoice"] = invoice_result
                    entry["status"] = "invoiced"
                except ValueError as exc:
                    entry["status"] = "reported"
                    entry["invoice_error"] = str(exc)
            else:
                entry["status"] = report_result.get("status", "processed")
            results.append(entry)

        return {
            "status": "completed",
            "processed": len(results),
            "auto_invoice": settings.BILLING_OVERAGE_AUTO_INVOICE,
            "completed_at": datetime.now(UTC).isoformat(),
            "results": results,
        }
