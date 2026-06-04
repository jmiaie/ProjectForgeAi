import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.autoscale import compute_autoscale_hooks
from core.config import settings
from fastapi.testclient import TestClient
from tenancy.billing import TenantBillingService, TenantUsageStore
from tenancy.billing_scheduler import BillingSchedulerService
from tenancy.data_portability import TenantDataPortabilityService
from tenancy.registry import TenantRegistry
from tenancy.stripe_billing import StripeBillingService
from tenancy.usage_metering import UsageMeteringService

import main


class Sprint27Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_BILLING_ROOT = str(root / "billing")
        settings.TENANT_USAGE_ROOT = str(root / "usage")
        settings.TENANT_EXPORT_ROOT = str(root / "exports")
        settings.DEFAULT_TENANT_ID = "tenant_default"
        settings.BILLING_OVERAGE_SCHEDULER_ENABLED = False
        settings.BILLING_OVERAGE_AUTO_INVOICE = True

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_billing_scheduler_disabled(self):
        scheduler = BillingSchedulerService()
        result = await scheduler.run_scheduled_billing()
        self.assertEqual(result["status"], "disabled")

    async def test_billing_scheduler_processes_overage(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Sched Co", tier="starter", tenant_id="tenant_sched")
        usage_store = TenantUsageStore()
        usage_store.record_llm_tokens(tenant.tenant_id, 150_000)
        metering = UsageMeteringService(
            billing_service=TenantBillingService(tenant_registry=registry, usage_store=usage_store),
        )
        scheduler = BillingSchedulerService(metering=metering)
        with patch.object(settings, "BILLING_OVERAGE_SCHEDULER_ENABLED", True):
            with patch.object(settings, "STRIPE_MOCK", True):
                with patch.object(settings, "BILLING_OVERAGE_AUTO_INVOICE", False):
                    result = await scheduler.run_scheduled_billing(tenant.tenant_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["results"][0]["status"], "reported")

    def test_billing_schedule_api_disabled(self):
        client = TestClient(main.app)
        response = client.post("/api/v1/billing/schedule/run")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "disabled")

    def test_tenant_export_import_roundtrip(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Export Co", tier="pro", tenant_id="tenant_exp", region="us-east-1")
        portability = TenantDataPortabilityService()
        exported = portability.export_tenant_data(tenant.tenant_id)
        self.assertEqual(exported["status"], "exported")
        export_id = exported["export_id"]

        listed = portability.list_exports(tenant.tenant_id)
        self.assertEqual(len(listed["exports"]), 1)

        imported = portability.import_tenant_data(tenant.tenant_id, export_id=export_id)
        self.assertEqual(imported["status"], "imported")

    def test_tenant_export_api(self):
        registry = TenantRegistry()
        registry.create(name="API Export", tier="starter", tenant_id="tenant_api_exp")
        client = TestClient(main.app)
        response = client.post("/api/v1/tenants/tenant_api_exp/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("export_id", response.json())

    def test_tenant_import_api(self):
        registry = TenantRegistry()
        tenant_id = "tenant_api_imp"
        registry.create(name="API Import", tier="starter", tenant_id=tenant_id)
        portability = TenantDataPortabilityService()
        exported = portability.export_tenant_data(tenant_id)
        client = TestClient(main.app)
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/import",
            json={"export_id": exported["export_id"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "imported")

    def test_region_migrate_with_import(self):
        registry = TenantRegistry()
        tenant_id = "tenant_mig_imp"
        registry.create(name="Migrate Import", tier="pro", tenant_id=tenant_id, region="us-east-1")
        portability = TenantDataPortabilityService()
        exported = portability.export_tenant_data(tenant_id)
        client = TestClient(main.app)
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/region/migrate",
            json={"target_region": "eu-west-1", "import_export_id": exported["export_id"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["region"]["region_id"], "eu-west-1")
        self.assertEqual(response.json()["import"]["status"], "imported")

    def test_invoice_finalized_webhook(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Final Co", tier="starter", tenant_id="tenant_fin")
        service = StripeBillingService(tenant_registry=registry)
        invoice = service.invoice_store.create(
            tenant_id=tenant.tenant_id,
            amount_cents=500,
            currency="usd",
            description="LLM overage",
        )
        invoice_id = invoice["invoice_id"]
        service.invoice_store.save(invoice)
        event = {
            "id": "evt_final",
            "type": "invoice.finalized",
            "data": {
                "object": {
                    "id": "in_stripe_final",
                    "status": "paid",
                    "metadata": {"tenant_id": tenant.tenant_id, "invoice_id": invoice_id},
                }
            },
        }
        with patch.object(settings, "STRIPE_MOCK", True):
            result = service.handle_webhook(json.dumps(event).encode(), None)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["event_type"], "invoice.finalized")
        self.assertEqual(result["invoice"]["status"], "paid")

    def test_autoscale_hooks(self):
        hooks = compute_autoscale_hooks()
        self.assertIn("hooks", hooks)
        self.assertEqual(hooks["hooks"][0]["target"], "backend")
        self.assertIn("recommended_replicas", hooks["hooks"][0])

    def test_autoscale_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/observability/autoscale")
        self.assertEqual(response.status_code, 200)
        self.assertIn("hooks", response.json())

    def test_billing_overage_cronjob_template(self):
        template = (
            Path(__file__).resolve().parents[3]
            / "deploy/helm/projectforge/templates/billing-overage-cronjob.yaml"
        )
        self.assertTrue(template.exists())

    def test_autoscale_doc_exists(self):
        doc = Path(__file__).resolve().parents[3] / "deploy/observability/AUTOSCALE.md"
        self.assertTrue(doc.exists())


if __name__ == "__main__":
    unittest.main()
