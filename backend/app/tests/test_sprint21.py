import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from fastapi.testclient import TestClient
from graph.adapter import Neo4jGraphAdapter
from graph.models import GraphNode, NodeLabel, ProjectGraph
from tenancy.neo4j_isolation import TenantNeo4jRegistry, create_graph_adapter, tenant_database_name
from tenancy.stripe_billing import StripeBillingService

import main


class Sprint21Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_BILLING_ROOT = str(root / "billing")
        settings.DEFAULT_TENANT_ID = "tenant_default"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tenant_database_name_sanitized(self):
        self.assertTrue(tenant_database_name("tenant_acme-corp").startswith("pf"))

    def test_neo4j_registry_ensure_database(self):
        with patch.object(settings, "NEO4J_TENANT_ISOLATION_ENABLED", True):
            registry = TenantNeo4jRegistry()
            record = registry.ensure_database("tenant_acme")
        self.assertEqual(record["tenant_id"], "tenant_acme")
        self.assertIn("database", record)

    def test_graph_adapter_tags_nodes_with_tenant(self):
        adapter = Neo4jGraphAdapter(tenant_id="tenant_a")
        graph = ProjectGraph(
            project_id="proj_x",
            nodes=[GraphNode(id="n1", label=NodeLabel.PROJECT, properties={"project_id": "proj_x"})],
        )
        tagged = adapter._graph_with_tenant(graph)
        self.assertEqual(tagged.nodes[0].properties.get("tenant_id"), "tenant_a")

    def test_create_graph_adapter_when_isolation_enabled(self):
        with patch.object(settings, "NEO4J_TENANT_ISOLATION_ENABLED", True):
            adapter = create_graph_adapter("tenant_iso")
        self.assertEqual(adapter.tenant_id, "tenant_iso")
        self.assertIsNotNone(adapter.database)

    async def test_mock_stripe_checkout(self):
        from tenancy.registry import TenantRegistry

        registry = TenantRegistry()
        tenant = registry.create(name="Paid Co", tier="pro", tenant_id="tenant_paid")
        service = StripeBillingService(tenant_registry=registry)
        with patch.object(settings, "STRIPE_MOCK", True):
            result = await service.create_checkout(tenant.tenant_id)
        self.assertEqual(result["mode"], "mock")
        self.assertIn("checkout_url", result)

    def test_billing_checkout_api(self):
        client = TestClient(main.app)
        response = client.post("/api/v1/tenants/tenant_default/billing/checkout", json={})
        self.assertEqual(response.status_code, 200)
        self.assertIn("checkout_url", response.json())

    def test_grafana_dashboard_file_exists(self):
        dashboard = Path(__file__).resolve().parents[3] / "deploy/observability/grafana/dashboards/projectforge-overview.json"
        self.assertTrue(dashboard.exists())


if __name__ == "__main__":
    unittest.main()
