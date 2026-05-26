import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from fastapi.testclient import TestClient
from tenancy.billing import TenantBillingService, TenantUsageStore
from tenancy.neo4j_cluster import run_auto_heal
from tenancy.regions import TenantRegionRegistry, ensure_tenant_region, list_region_catalog
from tenancy.registry import TenantRegistry
from tenancy.usage_metering import UsageMeteringService

import main


class Sprint25Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_BILLING_ROOT = str(root / "billing")
        settings.TENANT_USAGE_ROOT = str(root / "usage")
        settings.DEFAULT_TENANT_ID = "tenant_default"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_overage_summary_when_over_quota(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Over Co", tier="starter", tenant_id="tenant_over")
        usage_store = TenantUsageStore()
        usage_store.record_llm_tokens(tenant.tenant_id, 150_000)
        metering = UsageMeteringService(
            billing_service=TenantBillingService(tenant_registry=registry, usage_store=usage_store),
        )
        summary = metering.overage_summary(tenant.tenant_id)
        self.assertEqual(summary["overage_tokens"], 50_000)
        self.assertGreater(summary["estimated_cents"], 0)

    async def test_mock_report_llm_overage(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Meter Co", tier="starter", tenant_id="tenant_meter")
        usage_store = TenantUsageStore()
        usage_store.record_llm_tokens(tenant.tenant_id, 200_000)
        from tenancy.stripe_billing import StripeBillingService

        stripe = StripeBillingService(tenant_registry=registry)
        stripe.subscription_store.save(
            {
                "subscription_id": "sub_test",
                "tenant_id": tenant.tenant_id,
                "stripe_customer_id": "cus_mock_meter",
                "status": "active",
                "billing_mode": "subscription",
            }
        )
        metering = UsageMeteringService(
            billing_service=TenantBillingService(tenant_registry=registry, usage_store=usage_store),
            subscription_store=stripe.subscription_store,
        )
        with patch.object(settings, "STRIPE_MOCK", True):
            result = await metering.report_llm_overage(tenant.tenant_id)
        self.assertEqual(result["status"], "reported")

    def test_billing_overage_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/tenants/tenant_default/billing/overage")
        self.assertEqual(response.status_code, 200)
        self.assertIn("overage_tokens", response.json())

    def test_tenant_region_assignment(self):
        registry = TenantRegistry()
        tenant = registry.create(name="EU Co", tier="pro", tenant_id="tenant_eu", region="eu-west-1")
        region = TenantRegionRegistry().get(tenant.tenant_id)
        self.assertEqual(region["region_id"], "eu-west-1")
        self.assertEqual(region["residency_zone"], "eu")

    def test_region_validation_blocks_mismatch(self):
        registry = TenantRegistry()
        tenant = registry.create(name="US Co", tier="pro", tenant_id="tenant_us", region="us-east-1")
        with patch.object(settings, "TENANT_REGION_ROUTING_ENABLED", True):
            result = TenantRegionRegistry().validate_request(tenant.tenant_id, "eu-west-1")
        self.assertFalse(result["allowed"])

    def test_regions_catalog_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/regions")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["regions"]), 2)

    def test_tenant_region_api(self):
        ensure_tenant_region("tenant_default", "us-east-1")
        client = TestClient(main.app)
        response = client.get("/api/v1/tenants/tenant_default/region")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["region"]["region_id"], "us-east-1")

    def test_cluster_auto_heal_disabled_by_default(self):
        result = run_auto_heal()
        self.assertFalse(result["healed"])
        self.assertEqual(result["reason"], "auto_heal_disabled")

    def test_cluster_heal_api(self):
        with patch.object(settings, "NEO4J_CLUSTER_AUTO_HEAL_ENABLED", True):
            with patch("tenancy.neo4j_cluster.check_uri_health", return_value={"uri": "x", "healthy": True}):
                client = TestClient(main.app)
                response = client.post("/api/v1/neo4j/cluster/heal")
        self.assertEqual(response.status_code, 200)
        self.assertIn("actions", response.json())

    def test_k8s_autoheal_doc_exists(self):
        doc = Path(__file__).resolve().parents[3] / "deploy/neo4j/K8S_AUTOHEAL.md"
        self.assertTrue(doc.exists())

    def test_helm_autoheal_template_exists(self):
        template = Path(__file__).resolve().parents[3] / "deploy/helm/projectforge/templates/neo4j-autoheal-cronjob.yaml"
        self.assertTrue(template.exists())


if __name__ == "__main__":
    unittest.main()
