import hashlib
import hmac
import json
import os
import time
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

    def _tenant_dir(self, tenant_id: str) -> Path:
        tenant_dir = self.root / tenant_id
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir

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
        self.save(invoice)
        return invoice

    def save(self, invoice: dict[str, Any]) -> dict[str, Any]:
        tenant_id = invoice["tenant_id"]
        invoice_id = invoice["invoice_id"]
        self._tenant_dir(tenant_id)
        (self.root / tenant_id / f"{invoice_id}.json").write_text(
            json.dumps(invoice, indent=2, sort_keys=True)
        )
        return invoice

    def get(self, tenant_id: str, invoice_id: str) -> dict[str, Any] | None:
        path = self.root / tenant_id / f"{invoice_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def find_by_stripe_session_id(self, session_id: str) -> dict[str, Any] | None:
        if not self.root.exists():
            return None
        for tenant_dir in self.root.iterdir():
            if not tenant_dir.is_dir():
                continue
            for path in tenant_dir.glob("inv_*.json"):
                invoice = json.loads(path.read_text())
                if invoice.get("stripe_session_id") == session_id:
                    return invoice
        return None

    def mark_paid(
        self,
        *,
        tenant_id: str,
        invoice_id: str,
        stripe_event_id: str | None = None,
        paid_at: str | None = None,
    ) -> dict[str, Any] | None:
        invoice = self.get(tenant_id, invoice_id)
        if invoice is None:
            return None
        invoice["status"] = "paid"
        invoice["paid_at"] = paid_at or datetime.now(UTC).isoformat()
        if stripe_event_id:
            invoice["stripe_event_id"] = stripe_event_id
        return self.save(invoice)

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

    def _tier_for_amount(self, amount_cents: int) -> str | None:
        for tier, price in [("enterprise", 49900), ("pro", 9900)]:
            if amount_cents >= price:
                return tier
        return None

    async def create_checkout(
        self,
        tenant_id: str,
        *,
        success_url: str | None = None,
        target_tier: str | None = None,
    ) -> dict[str, Any]:
        tenant = self.tenant_registry.get(tenant_id)
        if tenant is None:
            if tenant_id == settings.DEFAULT_TENANT_ID:
                self.tenant_registry._ensure_default_tenant()
                tenant = self.tenant_registry.get(tenant_id)
            if tenant is None:
                raise ValueError(f"Unknown tenant: {tenant_id}")

        checkout_tier = (target_tier or tenant.tier).lower()
        amount = self._tier_price_cents(checkout_tier)
        description = f"ProjectForge {checkout_tier} plan — {tenant.name}"
        redirect = success_url or settings.FRONTEND_BASE_URL

        if settings.STRIPE_MOCK or not settings.STRIPE_SECRET_KEY:
            invoice = self.invoice_store.create(
                tenant_id=tenant_id,
                amount_cents=amount,
                currency="usd",
                description=description,
            )
            invoice["target_tier"] = checkout_tier
            self.invoice_store.save(invoice)
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
                    "metadata[target_tier]": checkout_tier,
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
        invoice["target_tier"] = checkout_tier
        invoice["status"] = "pending"
        self.invoice_store.save(invoice)
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
            "webhook_configured": bool(settings.STRIPE_WEBHOOK_SECRET) or settings.STRIPE_MOCK,
        }

    def _verify_webhook_signature(self, payload: bytes, signature_header: str) -> None:
        secret = settings.STRIPE_WEBHOOK_SECRET
        if not secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not configured")

        parts = {}
        for item in signature_header.split(","):
            key, _, value = item.partition("=")
            parts.setdefault(key, []).append(value)

        timestamp = parts.get("t", [None])[0]
        signatures = parts.get("v1", [])
        if not timestamp or not signatures:
            raise ValueError("Invalid Stripe signature header")

        if abs(time.time() - int(timestamp)) > 300:
            raise ValueError("Stripe webhook timestamp outside tolerance")

        signed_payload = f"{timestamp}.{payload.decode()}".encode()
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, signature) for signature in signatures):
            raise ValueError("Stripe webhook signature verification failed")

    def handle_webhook(self, payload: bytes, signature_header: str | None = None) -> dict[str, Any]:
        if settings.STRIPE_MOCK:
            event = json.loads(payload)
        else:
            if not signature_header:
                raise ValueError("Missing Stripe-Signature header")
            self._verify_webhook_signature(payload, signature_header)
            event = json.loads(payload)

        return self._process_event(event)

    def _process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_type = event.get("type", "")
        event_id = event.get("id")
        data_object = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            return self._handle_checkout_completed(data_object, event_id)
        if event_type == "invoice.paid":
            return self._handle_invoice_paid(data_object, event_id)

        return {"status": "ignored", "event_type": event_type}

    def _handle_checkout_completed(self, session: dict[str, Any], event_id: str | None) -> dict[str, Any]:
        if session.get("payment_status") not in {None, "paid", "no_payment_required"}:
            return {"status": "ignored", "reason": "payment not completed"}

        tenant_id = (session.get("metadata") or {}).get("tenant_id")
        session_id = session.get("id")
        invoice = None
        if session_id:
            invoice = self.invoice_store.find_by_stripe_session_id(session_id)
        if invoice is None and tenant_id:
            metadata_invoice_id = (session.get("metadata") or {}).get("invoice_id")
            if metadata_invoice_id:
                invoice = self.invoice_store.get(tenant_id, metadata_invoice_id)

        if invoice is None:
            return {"status": "ignored", "reason": "invoice not found", "session_id": session_id}

        tenant_id = invoice["tenant_id"]
        updated = self.invoice_store.mark_paid(
            tenant_id=tenant_id,
            invoice_id=invoice["invoice_id"],
            stripe_event_id=event_id,
        )
        tier_update = self._apply_tier_upgrade(tenant_id, invoice)
        return {
            "status": "processed",
            "event_type": "checkout.session.completed",
            "invoice": updated,
            "tier_update": tier_update,
        }

    def _handle_invoice_paid(self, stripe_invoice: dict[str, Any], event_id: str | None) -> dict[str, Any]:
        metadata = stripe_invoice.get("metadata") or {}
        tenant_id = metadata.get("tenant_id")
        invoice_id = metadata.get("invoice_id")
        if not tenant_id or not invoice_id:
            return {"status": "ignored", "reason": "missing tenant or invoice metadata"}

        updated = self.invoice_store.mark_paid(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            stripe_event_id=event_id,
        )
        if updated is None:
            return {"status": "ignored", "reason": "invoice not found", "invoice_id": invoice_id}

        tier_update = self._apply_tier_upgrade(tenant_id, updated)
        return {
            "status": "processed",
            "event_type": "invoice.paid",
            "invoice": updated,
            "tier_update": tier_update,
        }

    def _apply_tier_upgrade(self, tenant_id: str, invoice: dict[str, Any]) -> dict[str, Any] | None:
        target_tier = invoice.get("target_tier")
        if not target_tier:
            target_tier = self._tier_for_amount(int(invoice.get("amount_cents", 0)))
        if not target_tier:
            return None

        tenant = self.tenant_registry.get(tenant_id)
        if tenant is None or tenant.tier == target_tier:
            return {"tenant_id": tenant_id, "tier": target_tier, "changed": False}

        updated = self.tenant_registry.update_tier(tenant_id, target_tier)
        return {"tenant_id": tenant_id, "tier": updated.tier, "changed": True}
