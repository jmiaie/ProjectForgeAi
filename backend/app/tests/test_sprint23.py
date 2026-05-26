import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.config import settings
from fastapi.testclient import TestClient
from graph.adapter import Neo4jGraphAdapter
from tenancy.neo4j_isolation import TenantNeo4jRegistry, resolve_read_uri, tenant_uses_read_replica
from tenancy.registry import TenantRegistry
from tenancy.stripe_billing import StripeBillingService

import main


class Sprint23Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_BILLING_ROOT = str(root / "billing")
        settings.DEFAULT_TENANT_ID = "tenant_default"

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_mock_subscription_checkout(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Sub Co", tier="starter", tenant_id="tenant_sub")
        service = StripeBillingService(tenant_registry=registry)
        with patch.object(settings, "STRIPE_MOCK", True):
            result = await service.create_subscription(tenant.tenant_id, target_tier="pro")
        self.assertEqual(result["billing_mode"], "subscription")
        self.assertEqual(result["subscription"]["status"], "active")
        self.assertEqual(registry.get(tenant.tenant_id).tier, "pro")

    def test_subscription_webhook_updated(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Ent Co", tier="pro", tenant_id="tenant_ent")
        service = StripeBillingService(tenant_registry=registry)
        service.subscription_store.save(
            {
                "subscription_id": "sub_local",
                "tenant_id": tenant.tenant_id,
                "stripe_subscription_id": "sub_stripe_1",
                "target_tier": "enterprise",
                "status": "pending",
                "billing_mode": "subscription",
            }
        )
        event = {
            "id": "evt_sub",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_stripe_1",
                    "status": "active",
                    "current_period_end": 1893456000,
                    "metadata": {"tenant_id": tenant.tenant_id, "target_tier": "enterprise"},
                }
            },
        }
        with patch.object(settings, "STRIPE_MOCK", True):
            result = service.handle_webhook(json.dumps(event).encode(), None)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(registry.get(tenant.tenant_id).tier, "enterprise")

    def test_billing_subscribe_api(self):
        client = TestClient(main.app)
        with patch.object(settings, "STRIPE_MOCK", True):
            response = client.post(
                "/api/v1/tenants/tenant_default/billing/subscribe",
                json={"target_tier": "pro"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["billing_mode"], "subscription")

    def test_read_replica_routing_for_enterprise(self):
        registry = TenantRegistry()
        registry.create(name="Big Co", tier="enterprise", tenant_id="tenant_big")
        with patch.object(settings, "NEO4J_READ_REPLICA_ENABLED", True):
            with patch.object(settings, "NEO4J_READ_REPLICA_URI", "bolt://neo4j-replica:7687"):
                self.assertTrue(tenant_uses_read_replica("tenant_big"))
                self.assertEqual(resolve_read_uri("tenant_big"), "bolt://neo4j-replica:7687")

    def test_read_replica_skipped_for_starter(self):
        registry = TenantRegistry()
        registry.create(name="Small Co", tier="starter", tenant_id="tenant_small")
        with patch.object(settings, "NEO4J_READ_REPLICA_ENABLED", True):
            with patch.object(settings, "NEO4J_READ_REPLICA_URI", "bolt://neo4j-replica:7687"):
                self.assertFalse(tenant_uses_read_replica("tenant_small"))

    def test_neo4j_adapter_read_session_uses_replica_driver(self):
        Neo4jGraphAdapter._native_disabled_warning = None
        mock_write_driver = MagicMock()
        mock_read_driver = MagicMock()
        mock_write_driver.verify_connectivity.return_value = None
        mock_read_driver.verify_connectivity.return_value = None
        mock_read_session = MagicMock()
        mock_read_driver.session.return_value.__enter__.return_value = mock_read_session
        mock_read_session.execute_read.return_value = None

        with patch("neo4j.GraphDatabase") as graph_db:
            graph_db.driver.side_effect = [mock_write_driver, mock_read_driver]
            with patch.object(settings, "NEO4J_BOOTSTRAP_ON_CONNECT", False):
                adapter = Neo4jGraphAdapter(read_uri="bolt://neo4j-replica:7687")
        adapter.get_graph("proj_test")
        mock_read_driver.session.assert_called()

    def test_alert_rules_file_exists(self):
        alerts = Path(__file__).resolve().parents[3] / "deploy/observability/grafana/alerts/projectforge-alerts.yaml"
        self.assertTrue(alerts.exists())
        self.assertIn("ProjectForgeHighErrorRate", alerts.read_text())

    def test_runbook_exists(self):
        runbook = Path(__file__).resolve().parents[3] / "deploy/observability/RUNBOOK.md"
        self.assertTrue(runbook.exists())


if __name__ == "__main__":
    unittest.main()
