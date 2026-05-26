import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from core.config import settings
from tenancy.registry import TenantRegistry


class InvoiceStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_BILLING_ROOT)

    def create(self, *, tenant_id: str, amount_cents: int, currency: str, description: str) -> dict[str, Any]:
        invoice = {
            "invoice_id": f"inv_{uuid4().hex}",
            "tenant_id": tenant_id,
            "amount_cents": amount_cents,
            "currency": currency,
            "description": description,
            "status": "open",
            "provider": "stripe" if not settings.STRIPE_MOCK else "mock",
            "created_at": datetime.now(UTC).isoformat(),
        }
        tenant_dir = self.root / tenant_id
        os.makedirs(tenant_dir, exist_ok=True)
        (tenant_dir / f"{invoice['invoice_id']}.json").write_text(json.dumps(invoice, indent=2, sort_keys=True))
        return invoice

    def list_invoices(self, tenant_id: str) -> list[dict[str, Any]]:
        tenant_dir = self.root / tenant_id
        if not tenant_dir.exists():
            return []
        return [json.loads(path.read_text()) for path in sorted(tenant_dir.glob("inv_*.json"))]


class StripeBillingService:
    def __init__(
        self,
        tenant_registry: TenantRegistry | None = None,
        invoice_store: InvoiceStore | None = None,
    ):
        self.tenant_registry = tenant_registry or TenantRegistry()
        self.invoice_store = invoice_store or InvoiceStore()

    def _tier_price_cents(self, tier: str) -> int:
        return {
            "starter": 0,
            "pro": 9900,
            "enterprise": 49900,
        }.get(tier.lower(), 0)

    async def create_checkout(self, tenant_id: str, *, success_url: str | None = None) -> dict[str, Any]:
        tenant = self.tenant_registry.get(tenant_id)
        if tenant is None:
            if tenant_id == settings.DEFAULT_TENANT_ID:
                self.tenant_registry._ensure_default_tenant()
                tenant = self.tenant_registry.get(tenant_id)
            if tenant is None:
                raise ValueError(f"Unknown tenant: {tenant_id}")

        amount = self._tier_price_cents(tenant.tier)
        description = f"ProjectForge {tenant.tier} plan — {tenant.name}"
        redirect = success_url or settings.FRONTEND_BASE_URL

        if settings.STRIPE_MOCK or not settings.STRIPE_SECRET_KEY:
            invoice = self.invoice_store.create(
                tenant_id=tenant_id,
                amount_cents=amount,
                currency="usd",
                description=description,
            )
            return {
                "mode": "mock",
                "checkout_url": f"{redirect}/portfolio?billing=mock&invoice_id={invoice['invoice_id']}",
                "invoice": invoice,
            }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                auth=(settings.STRIPE_SECRET_KEY, ""),
                data={
                    "mode": "payment",
                    "success_url": redirect,
                    "cancel_url": redirect,
                    "line_items[0][price_data][currency]": "usd",
                    "line_items[0][price_data][unit_amount]": amount,
                    "line_items[0][price_data][product_data][name]": description,
                    "line_items[0][quantity]": 1,
                    "metadata[tenant_id]": tenant_id,
                },
            )
            response.raise_for_status()
            payload = response.json()

        invoice = self.invoice_store.create(
            tenant_id=tenant_id,
            amount_cents=amount,
            currency="usd",
            description=description,
        )
        invoice["stripe_session_id"] = payload.get("id")
        invoice["status"] = "pending"
        return {
            "mode": "stripe",
            "checkout_url": payload.get("url"),
            "session_id": payload.get("id"),
            "invoice": invoice,
        }

    def list_invoices(self, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "invoices": self.invoice_store.list_invoices(tenant_id),
            "mock_mode": settings.STRIPE_MOCK,
        }

    def billing_status(self) -> dict[str, Any]:
        return {
            "provider": "stripe",
            "mock_mode": settings.STRIPE_MOCK,
            "configured": bool(settings.STRIPE_SECRET_KEY) or settings.STRIPE_MOCK,
        }
