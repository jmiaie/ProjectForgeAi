import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.config import settings
from core.observability import metrics_collector
from core.slo import compute_slo_status
from fastapi.testclient import TestClient
from graph.adapter import Neo4jGraphAdapter
from tenancy.neo4j_cluster import check_cluster_health, cluster_uris, select_write_uri
from tenancy.registry import TenantRegistry
from tenancy.stripe_billing import StripeBillingService

import main


class Sprint24Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_BILLING_ROOT = str(root / "billing")
        settings.DEFAULT_TENANT_ID = "tenant_default"

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_mock_customer_portal(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Portal Co", tier="pro", tenant_id="tenant_portal")
        service = StripeBillingService(tenant_registry=registry)
        with patch.object(settings, "STRIPE_MOCK", True):
            await service.create_subscription(tenant.tenant_id, target_tier="pro")
            result = await service.create_customer_portal(tenant.tenant_id)
        self.assertEqual(result["mode"], "mock")
        self.assertIn("portal_url", result)

    async def test_mock_cancel_subscription(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Cancel Co", tier="pro", tenant_id="tenant_cancel")
        service = StripeBillingService(tenant_registry=registry)
        with patch.object(settings, "STRIPE_MOCK", True):
            await service.create_subscription(tenant.tenant_id, target_tier="pro")
            result = await service.cancel_subscription(tenant.tenant_id, at_period_end=False)
        self.assertEqual(result["status"], "canceled")
        self.assertEqual(registry.get(tenant.tenant_id).tier, "starter")

    def test_billing_portal_api(self):
        client = TestClient(main.app)
        with patch.object(settings, "STRIPE_MOCK", True):
            client.post(
                "/api/v1/tenants/tenant_default/billing/subscribe",
                json={"target_tier": "pro"},
            )
            response = client.post("/api/v1/tenants/tenant_default/billing/portal", json={})
        self.assertEqual(response.status_code, 200)
        self.assertIn("portal_url", response.json())

    def test_cancel_subscription_api(self):
        client = TestClient(main.app)
        with patch.object(settings, "STRIPE_MOCK", True):
            client.post(
                "/api/v1/tenants/tenant_default/billing/subscribe",
                json={"target_tier": "pro"},
            )
            response = client.post(
                "/api/v1/tenants/tenant_default/billing/subscription/cancel",
                json={"at_period_end": False},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "canceled")

    def test_cluster_uris_deduplicates(self):
        with patch.object(settings, "NEO4J_URI", "bolt://neo4j:7687"):
            with patch.object(settings, "NEO4J_CLUSTER_URIS", "bolt://neo4j:7687,bolt://neo4j-2:7687"):
                uris = cluster_uris()
        self.assertEqual(len(uris), 2)
        self.assertEqual(uris[0], "bolt://neo4j:7687")

    def test_cluster_health_check(self):
        with patch("tenancy.neo4j_cluster.check_uri_health") as check:
            check.return_value = {"uri": "bolt://neo4j-2:7687", "healthy": True}
            with patch.object(settings, "NEO4J_CLUSTER_FAILOVER_ENABLED", True):
                with patch.object(settings, "NEO4J_CLUSTER_URIS", "bolt://neo4j-2:7687"):
                    status = check_cluster_health()
        self.assertEqual(status["healthy_count"], 2)

    def test_select_write_uri_failover(self):
        with patch("tenancy.neo4j_cluster.check_uri_health") as check:
            check.side_effect = [
                {"uri": "bolt://neo4j:7687", "healthy": False},
                {"uri": "bolt://neo4j-2:7687", "healthy": True},
            ]
            with patch.object(settings, "NEO4J_CLUSTER_FAILOVER_ENABLED", True):
                with patch.object(settings, "NEO4J_CLUSTER_URIS", "bolt://neo4j-2:7687"):
                    self.assertEqual(select_write_uri(), "bolt://neo4j-2:7687")

    def test_neo4j_cluster_status_api(self):
        with patch("tenancy.neo4j_cluster.check_uri_health", return_value={"uri": "x", "healthy": True}):
            client = TestClient(main.app)
            response = client.get("/api/v1/neo4j/cluster/status")
        self.assertEqual(response.status_code, 200)
        self.assertIn("members", response.json())

    def test_slo_status_computes_error_budget(self):
        metrics_collector.record(route="/health", status_code=200, latency_ms=50)
        metrics_collector.record(route="/fail", status_code=500, latency_ms=100)
        status = compute_slo_status()
        self.assertIn("error_budget", status)
        self.assertIn("slos", status)

    def test_slo_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/observability/slo")
        self.assertEqual(response.status_code, 200)
        self.assertIn("overall_met", response.json())

    def test_adapter_uses_cluster_failover(self):
        Neo4jGraphAdapter._native_disabled_warning = None
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        with patch("tenancy.neo4j_cluster.connect_with_failover", return_value=(mock_driver, "bolt://neo4j-2:7687")):
            with patch.object(settings, "NEO4J_CLUSTER_FAILOVER_ENABLED", True):
                with patch.object(settings, "NEO4J_BOOTSTRAP_ON_CONNECT", False):
                    adapter = Neo4jGraphAdapter()
        self.assertEqual(adapter._write_uri, "bolt://neo4j-2:7687")

    def test_slo_dashboard_exists(self):
        dashboard = Path(__file__).resolve().parents[3] / "deploy/observability/grafana/dashboards/projectforge-slo.json"
        self.assertTrue(dashboard.exists())


if __name__ == "__main__":
    unittest.main()
