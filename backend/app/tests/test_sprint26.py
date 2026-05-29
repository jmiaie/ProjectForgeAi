import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.capacity import compute_capacity_plan
from core.config import settings
from fastapi.testclient import TestClient
from tenancy.billing import TenantBillingService, TenantUsageStore
from tenancy.migration import TenantMigrationService, region_read_replica_map, resolve_region_read_uri
from tenancy.registry import TenantRegistry
from tenancy.usage_metering import UsageMeteringService

import main


class Sprint26Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_BILLING_ROOT = str(root / "billing")
        settings.TENANT_USAGE_ROOT = str(root / "usage")
        settings.DEFAULT_TENANT_ID = "tenant_default"

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_create_overage_invoice_with_line_items(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Invoice Co", tier="starter", tenant_id="tenant_inv")
        usage_store = TenantUsageStore()
        usage_store.record_llm_tokens(tenant.tenant_id, 150_000)
        metering = UsageMeteringService(
            billing_service=TenantBillingService(tenant_registry=registry, usage_store=usage_store),
        )
        with patch.object(settings, "STRIPE_MOCK", True):
            await metering.report_llm_overage(tenant.tenant_id)
            result = await metering.create_overage_invoice(tenant.tenant_id)
        self.assertIn("line_items", result["invoice"])
        self.assertEqual(result["invoice"]["line_items"][0]["type"], "llm_overage")

    def test_billing_overage_invoice_api(self):
        from tenancy.billing import TenantUsageStore

        usage_store = TenantUsageStore()
        usage_store.record_llm_tokens("tenant_default", 150_000)
        client = TestClient(main.app)
        with patch.object(settings, "STRIPE_MOCK", True):
            client.post("/api/v1/tenants/tenant_default/billing/usage/report")
            response = client.post("/api/v1/tenants/tenant_default/billing/overage/invoice")
        self.assertEqual(response.status_code, 200)
        self.assertIn("line_items", response.json()["invoice"])

    def test_region_read_replica_map(self):
        with patch.object(
            settings,
            "REGION_READ_REPLICA_URIS",
            "us-east-1:bolt://neo4j-us:7687,eu-west-1:bolt://neo4j-eu:7687",
        ):
            replicas = region_read_replica_map()
        self.assertEqual(replicas["eu-west-1"], "bolt://neo4j-eu:7687")

    def test_tenant_region_migration(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Move Co", tier="pro", tenant_id="tenant_move", region="us-east-1")
        service = TenantMigrationService()
        result = service.migrate_region(tenant.tenant_id, "eu-west-1")
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["region"]["region_id"], "eu-west-1")

    def test_region_migration_api(self):
        client = TestClient(main.app)
        response = client.post(
            "/api/v1/tenants/tenant_default/region/migrate",
            json={"target_region": "eu-west-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["region"]["region_id"], "eu-west-1")

    def test_resolve_region_read_uri(self):
        with patch.object(settings, "TENANT_REGION_READ_REPLICAS_ENABLED", True):
            with patch.object(settings, "REGION_READ_REPLICA_URIS", "eu-west-1:bolt://neo4j-eu:7687"):
                self.assertEqual(resolve_region_read_uri("eu-west-1"), "bolt://neo4j-eu:7687")

    def test_capacity_plan_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/observability/capacity")
        self.assertEqual(response.status_code, 200)
        self.assertIn("recommendations", response.json())

    def test_capacity_plan_recommendations(self):
        plan = compute_capacity_plan()
        self.assertIn("recommendations", plan)
        self.assertGreaterEqual(len(plan["recommendations"]), 1)

    def test_capacity_dashboard_exists(self):
        dashboard = Path(__file__).resolve().parents[3] / "deploy/observability/grafana/dashboards/projectforge-capacity.json"
        self.assertTrue(dashboard.exists())


if __name__ == "__main__":
    unittest.main()
