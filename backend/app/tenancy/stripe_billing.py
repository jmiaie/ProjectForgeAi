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


class SubscriptionStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.TENANT_BILLING_ROOT)

    def _path(self, tenant_id: str) -> Path:
        tenant_dir = self.root / tenant_id
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir / "subscription.json"

    def get(self, tenant_id: str) -> dict[str, Any] | None:
        path = self._path(tenant_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save(self, subscription: dict[str, Any]) -> dict[str, Any]:
        path = self._path(subscription["tenant_id"])
        path.write_text(json.dumps(subscription, indent=2, sort_keys=True))
        return subscription

    def find_by_stripe_id(self, stripe_subscription_id: str) -> dict[str, Any] | None:
        if not self.root.exists():
            return None
        for tenant_dir in self.root.iterdir():
            if not tenant_dir.is_dir():
                continue
            path = tenant_dir / "subscription.json"
            if not path.exists():
                continue
            subscription = json.loads(path.read_text())
            if subscription.get("stripe_subscription_id") == stripe_subscription_id:
                return subscription
        return None


class StripeBillingService:
    def __init__(
        self,
        tenant_registry: TenantRegistry | None = None,
        invoice_store: InvoiceStore | None = None,
        subscription_store: SubscriptionStore | None = None,
    ):
        self.tenant_registry = tenant_registry or TenantRegistry()
        self.invoice_store = invoice_store or InvoiceStore()
        self.subscription_store = subscription_store or SubscriptionStore()

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

    def _stripe_price_id(self, tier: str) -> str | None:
        return {
            "pro": settings.STRIPE_PRO_PRICE_ID,
            "enterprise": settings.STRIPE_ENTERPRISE_PRICE_ID,
        }.get(tier.lower())

    def _resolve_tenant(self, tenant_id: str):
        tenant = self.tenant_registry.get(tenant_id)
        if tenant is None:
            if tenant_id == settings.DEFAULT_TENANT_ID:
                self.tenant_registry._ensure_default_tenant()
                tenant = self.tenant_registry.get(tenant_id)
            if tenant is None:
                raise ValueError(f"Unknown tenant: {tenant_id}")
        return tenant

    async def create_checkout(
        self,
        tenant_id: str,
        *,
        success_url: str | None = None,
        target_tier: str | None = None,
        billing_mode: str = "payment",
    ) -> dict[str, Any]:
        if billing_mode == "subscription":
            return await self.create_subscription(tenant_id, success_url=success_url, target_tier=target_tier)

        tenant = self._resolve_tenant(tenant_id)

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

    async def create_subscription(
        self,
        tenant_id: str,
        *,
        success_url: str | None = None,
        target_tier: str | None = None,
    ) -> dict[str, Any]:
        tenant = self._resolve_tenant(tenant_id)
        checkout_tier = (target_tier or tenant.tier).lower()
        if checkout_tier == "starter":
            raise ValueError("Starter tier has no subscription plan; choose pro or enterprise")

        amount = self._tier_price_cents(checkout_tier)
        description = f"ProjectForge {checkout_tier} subscription — {tenant.name}"
        redirect = success_url or settings.FRONTEND_BASE_URL

        if settings.STRIPE_MOCK or not settings.STRIPE_SECRET_KEY:
            subscription = {
                "subscription_id": f"sub_{uuid4().hex}",
                "tenant_id": tenant_id,
                "target_tier": checkout_tier,
                "amount_cents": amount,
                "currency": "usd",
                "status": "active",
                "billing_mode": "subscription",
                "provider": "mock",
                "created_at": datetime.now(UTC).isoformat(),
                "current_period_end": datetime.now(UTC).isoformat(),
            }
            self.subscription_store.save(subscription)
            self.tenant_registry.update_tier(tenant_id, checkout_tier)
            return {
                "mode": "mock",
                "billing_mode": "subscription",
                "checkout_url": f"{redirect}/portfolio?billing=subscription&subscription_id={subscription['subscription_id']}",
                "subscription": subscription,
            }

        price_id = self._stripe_price_id(checkout_tier)
        data: dict[str, str] = {
            "mode": "subscription",
            "success_url": redirect,
            "cancel_url": redirect,
            "metadata[tenant_id]": tenant_id,
            "metadata[target_tier]": checkout_tier,
            "subscription_data[metadata][tenant_id]": tenant_id,
            "subscription_data[metadata][target_tier]": checkout_tier,
        }
        if price_id:
            data["line_items[0][price]"] = price_id
            data["line_items[0][quantity]"] = "1"
        else:
            data["line_items[0][price_data][currency]"] = "usd"
            data["line_items[0][price_data][unit_amount]"] = str(amount)
            data["line_items[0][price_data][recurring][interval]"] = "month"
            data["line_items[0][price_data][product_data][name]"] = description
            data["line_items[0][quantity]"] = "1"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                auth=(settings.STRIPE_SECRET_KEY, ""),
                data=data,
            )
            response.raise_for_status()
            payload = response.json()

        subscription = {
            "subscription_id": f"sub_{uuid4().hex}",
            "tenant_id": tenant_id,
            "target_tier": checkout_tier,
            "amount_cents": amount,
            "currency": "usd",
            "status": "pending",
            "billing_mode": "subscription",
            "provider": "stripe",
            "stripe_session_id": payload.get("id"),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.subscription_store.save(subscription)
        return {
            "mode": "stripe",
            "billing_mode": "subscription",
            "checkout_url": payload.get("url"),
            "session_id": payload.get("id"),
            "subscription": subscription,
        }

    def get_subscription(self, tenant_id: str) -> dict[str, Any]:
        subscription = self.subscription_store.get(tenant_id)
        return {
            "tenant_id": tenant_id,
            "subscription": subscription,
            "mock_mode": settings.STRIPE_MOCK,
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
            "subscriptions_enabled": True,
            "price_ids": {
                "pro": settings.STRIPE_PRO_PRICE_ID,
                "enterprise": settings.STRIPE_ENTERPRISE_PRICE_ID,
            },
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
        if event_type == "customer.subscription.updated":
            return self._handle_subscription_updated(data_object, event_id)
        if event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(data_object, event_id)

        return {"status": "ignored", "event_type": event_type}

    def _activate_subscription(
        self,
        *,
        tenant_id: str,
        stripe_subscription_id: str | None = None,
        target_tier: str | None = None,
        status: str = "active",
        current_period_end: str | None = None,
    ) -> dict[str, Any]:
        subscription = self.subscription_store.get(tenant_id) or {
            "subscription_id": f"sub_{uuid4().hex}",
            "tenant_id": tenant_id,
            "billing_mode": "subscription",
            "provider": "stripe" if not settings.STRIPE_MOCK else "mock",
            "created_at": datetime.now(UTC).isoformat(),
        }
        subscription["status"] = status
        if stripe_subscription_id:
            subscription["stripe_subscription_id"] = stripe_subscription_id
        if target_tier:
            subscription["target_tier"] = target_tier
        if current_period_end:
            subscription["current_period_end"] = current_period_end
        self.subscription_store.save(subscription)
        tier_update = None
        if target_tier and status == "active":
            tier_update = self._apply_tier_upgrade(tenant_id, {"target_tier": target_tier})
        return {"subscription": subscription, "tier_update": tier_update}

    def _handle_subscription_updated(self, stripe_sub: dict[str, Any], event_id: str | None) -> dict[str, Any]:
        stripe_subscription_id = stripe_sub.get("id")
        subscription = self.subscription_store.find_by_stripe_id(stripe_subscription_id or "")
        metadata = stripe_sub.get("metadata") or {}
        tenant_id = metadata.get("tenant_id") or (subscription or {}).get("tenant_id")
        if not tenant_id:
            return {"status": "ignored", "reason": "tenant not found"}

        status_map = {
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "unpaid": "past_due",
            "trialing": "trialing",
        }
        status = status_map.get(stripe_sub.get("status", "active"), stripe_sub.get("status", "active"))
        target_tier = metadata.get("target_tier") or (subscription or {}).get("target_tier")
        period_end = stripe_sub.get("current_period_end")
        current_period_end = (
            datetime.fromtimestamp(int(period_end), UTC).isoformat() if period_end else None
        )
        result = self._activate_subscription(
            tenant_id=tenant_id,
            stripe_subscription_id=stripe_subscription_id,
            target_tier=target_tier,
            status=status,
            current_period_end=current_period_end,
        )
        return {
            "status": "processed",
            "event_type": "customer.subscription.updated",
            "stripe_event_id": event_id,
            **result,
        }

    def _handle_subscription_deleted(self, stripe_sub: dict[str, Any], event_id: str | None) -> dict[str, Any]:
        stripe_subscription_id = stripe_sub.get("id")
        subscription = self.subscription_store.find_by_stripe_id(stripe_subscription_id or "")
        if subscription is None:
            return {"status": "ignored", "reason": "subscription not found"}

        subscription["status"] = "canceled"
        subscription["canceled_at"] = datetime.now(UTC).isoformat()
        self.subscription_store.save(subscription)
        return {
            "status": "processed",
            "event_type": "customer.subscription.deleted",
            "stripe_event_id": event_id,
            "subscription": subscription,
        }

    def _handle_checkout_completed(self, session: dict[str, Any], event_id: str | None) -> dict[str, Any]:
        if session.get("mode") == "subscription":
            tenant_id = (session.get("metadata") or {}).get("tenant_id")
            target_tier = (session.get("metadata") or {}).get("target_tier")
            stripe_subscription_id = session.get("subscription")
            if tenant_id:
                result = self._activate_subscription(
                    tenant_id=tenant_id,
                    stripe_subscription_id=stripe_subscription_id,
                    target_tier=target_tier,
                    status="active",
                )
                return {
                    "status": "processed",
                    "event_type": "checkout.session.completed",
                    "billing_mode": "subscription",
                    **result,
                }

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
