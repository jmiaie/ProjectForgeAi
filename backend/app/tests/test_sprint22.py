import hashlib
import hmac
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.config import settings
from fastapi.testclient import TestClient
from tenancy.neo4j_isolation import TenantNeo4jRegistry, provision_tenant_database
from tenancy.registry import TenantRegistry
from tenancy.stripe_billing import InvoiceStore, StripeBillingService

import main


class Sprint22Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_BILLING_ROOT = str(root / "billing")
        settings.DEFAULT_TENANT_ID = "tenant_default"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_invoice_store_persists_stripe_session(self):
        store = InvoiceStore()
        invoice = store.create(
            tenant_id="tenant_a",
            amount_cents=9900,
            currency="usd",
            description="Pro plan",
        )
        invoice["stripe_session_id"] = "cs_test_123"
        store.save(invoice)
        found = store.find_by_stripe_session_id("cs_test_123")
        self.assertIsNotNone(found)
        self.assertEqual(found["invoice_id"], invoice["invoice_id"])

    def test_mock_webhook_marks_invoice_paid(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Paid Co", tier="starter", tenant_id="tenant_paid")
        service = StripeBillingService(tenant_registry=registry)
        with patch.object(settings, "STRIPE_MOCK", True):
            invoice = service.invoice_store.create(
                tenant_id=tenant.tenant_id,
                amount_cents=9900,
                currency="usd",
                description="Pro upgrade",
            )
            invoice["target_tier"] = "pro"
            invoice["stripe_session_id"] = "cs_mock_1"
            service.invoice_store.save(invoice)
            event = {
                "id": "evt_test",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_mock_1",
                        "payment_status": "paid",
                        "metadata": {"tenant_id": tenant.tenant_id},
                    }
                },
            }
            result = service.handle_webhook(json.dumps(event).encode(), None)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["invoice"]["status"], "paid")
        self.assertTrue(result["tier_update"]["changed"])
        self.assertEqual(registry.get(tenant.tenant_id).tier, "pro")

    def test_webhook_signature_verification(self):
        secret = "whsec_test_secret"
        payload = b'{"type":"invoice.paid"}'
        timestamp = str(int(time.time()))
        signed = hmac.new(
            secret.encode(),
            f"{timestamp}.{payload.decode()}".encode(),
            hashlib.sha256,
        ).hexdigest()
        signature = f"t={timestamp},v1={signed}"

        service = StripeBillingService()
        with patch.object(settings, "STRIPE_MOCK", False):
            with patch.object(settings, "STRIPE_WEBHOOK_SECRET", secret):
                service._verify_webhook_signature(payload, signature)

        with patch.object(settings, "STRIPE_MOCK", False):
            with patch.object(settings, "STRIPE_WEBHOOK_SECRET", secret):
                with self.assertRaises(ValueError):
                    service._verify_webhook_signature(payload, "t=1,v1=bad")

    def test_billing_webhook_api(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Webhook Co", tier="starter", tenant_id="tenant_wh")
        service = StripeBillingService(tenant_registry=registry)
        invoice = service.invoice_store.create(
            tenant_id=tenant.tenant_id,
            amount_cents=9900,
            currency="usd",
            description="Pro",
        )
        invoice["target_tier"] = "pro"
        invoice["stripe_session_id"] = "cs_api_1"
        service.invoice_store.save(invoice)

        client = TestClient(main.app)
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_api_1",
                    "payment_status": "paid",
                    "metadata": {"tenant_id": tenant.tenant_id},
                }
            },
        }
        with patch.object(settings, "STRIPE_MOCK", True):
            response = client.post("/api/v1/billing/webhook", json=event)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processed")

    def test_neo4j_provision_disabled_by_default(self):
        with patch.object(settings, "NEO4J_AUTO_PROVISION_DATABASES", False):
            result = provision_tenant_database("pftest")
        self.assertFalse(result["provisioned"])
        self.assertEqual(result["reason"], "auto_provision_disabled")

    def test_neo4j_registry_records_provision_attempt(self):
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.verify_connectivity.return_value = None

        with patch.object(settings, "NEO4J_TENANT_ISOLATION_ENABLED", True):
            with patch.object(settings, "NEO4J_AUTO_PROVISION_DATABASES", True):
                with patch("neo4j.GraphDatabase") as graph_db:
                    with patch("graph.bootstrap.bootstrap_neo4j") as bootstrap:
                        graph_db.driver.return_value = mock_driver
                        bootstrap.return_value = {"status": "bootstrapped"}
                        record = TenantNeo4jRegistry().ensure_database("tenant_acme")
        self.assertTrue(record["provisioned"])
        self.assertTrue(record["database"].startswith("pf"))

    def test_grafana_cloud_guide_exists(self):
        guide = Path(__file__).resolve().parents[3] / "deploy/observability/GRAFANA_CLOUD.md"
        self.assertTrue(guide.exists())
        self.assertIn("Grafana Cloud", guide.read_text())


if __name__ == "__main__":
    unittest.main()
