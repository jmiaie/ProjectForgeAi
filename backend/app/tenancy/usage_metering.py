"""Stripe usage-based metering for LLM token overages."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from core.config import settings
from tenancy.billing import TenantBillingService
from tenancy.stripe_billing import SubscriptionStore


class UsageReportStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_BILLING_ROOT)

    def _path(self, tenant_id: str) -> Path:
        tenant_dir = self.root / tenant_id
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir / "usage_reports.json"

    def append(self, tenant_id: str, report: dict[str, Any]) -> dict[str, Any]:
        path = self._path(tenant_id)
        records = json.loads(path.read_text()) if path.exists() else []
        records.append(report)
        path.write_text(json.dumps(records, indent=2, sort_keys=True))
        return report


class UsageMeteringService:
    def __init__(
        self,
        billing_service: TenantBillingService | None = None,
        subscription_store: SubscriptionStore | None = None,
        report_store: UsageReportStore | None = None,
    ):
        self.billing_service = billing_service or TenantBillingService()
        self.subscription_store = subscription_store or SubscriptionStore()
        self.report_store = report_store or UsageReportStore()

    def overage_summary(self, tenant_id: str) -> dict[str, Any]:
        status = self.billing_service.quota_status(tenant_id)
        llm_check = status["checks"]["max_llm_tokens"]
        limit = llm_check["limit"]
        current = int(llm_check["current"])
        if limit is None:
            overage_tokens = 0
        else:
            overage_tokens = max(0, current - int(limit))

        units = (overage_tokens + 999) // 1000 if overage_tokens else 0
        estimated_cents = units * settings.LLM_OVERAGE_CENTS_PER_1K
        return {
            "tenant_id": tenant_id,
            "tier": status["tier"],
            "llm_tokens": current,
            "llm_token_limit": limit,
            "overage_tokens": overage_tokens,
            "overage_units_1k": units,
            "estimated_cents": estimated_cents,
            "metered_billing_enabled": settings.STRIPE_METERED_BILLING_ENABLED,
        }

    async def report_llm_overage(self, tenant_id: str) -> dict[str, Any]:
        summary = self.overage_summary(tenant_id)
        if summary["overage_tokens"] <= 0:
            return {"status": "skipped", "reason": "no_overage", "summary": summary}

        subscription = self.subscription_store.get(tenant_id)
        customer_id = (subscription or {}).get("stripe_customer_id")
        report = {
            "report_id": f"urpt_{uuid4().hex}",
            "tenant_id": tenant_id,
            "event_name": settings.STRIPE_LLM_METER_EVENT_NAME,
            "quantity": summary["overage_units_1k"],
            "overage_tokens": summary["overage_tokens"],
            "estimated_cents": summary["estimated_cents"],
            "created_at": datetime.now(UTC).isoformat(),
        }

        if settings.STRIPE_MOCK or not settings.STRIPE_SECRET_KEY:
            report["mode"] = "mock"
            report["status"] = "reported"
            self.report_store.append(tenant_id, report)
            return {"status": "reported", "mode": "mock", "report": report, "summary": summary}

        if not customer_id:
            raise ValueError("No Stripe customer on file; subscribe before reporting metered usage")

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.stripe.com/v1/billing/meter_events",
                auth=(settings.STRIPE_SECRET_KEY, ""),
                data={
                    "event_name": settings.STRIPE_LLM_METER_EVENT_NAME,
                    "payload[stripe_customer_id]": customer_id,
                    "payload[value]": str(summary["overage_units_1k"]),
                },
            )
            response.raise_for_status()
            payload = response.json()

        report["mode"] = "stripe"
        report["status"] = "reported"
        report["stripe_event_id"] = payload.get("identifier")
        self.report_store.append(tenant_id, report)
        return {"status": "reported", "mode": "stripe", "report": report, "summary": summary}

    def list_reports(self, tenant_id: str) -> dict[str, Any]:
        path = self.report_store._path(tenant_id)
        if not path.exists():
            return {"tenant_id": tenant_id, "reports": []}
        return {"tenant_id": tenant_id, "reports": json.loads(path.read_text())}
