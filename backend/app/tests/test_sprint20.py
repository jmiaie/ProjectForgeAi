import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from core.otel_export import jaeger_trace_batch, prometheus_metrics_text
from fastapi.testclient import TestClient
from tenancy.billing import TenantBillingService, TenantUsageStore
from tenancy.registry import TenantRegistry

import main


class Sprint20Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.TENANT_USAGE_ROOT = str(root / "tenant-usage")
        settings.PROJECT_REGISTRY_ROOT = str(root / "projects")
        settings.DEFAULT_TENANT_ID = "tenant_default"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_prometheus_export_format(self):
        client = TestClient(main.app)
        client.get("/health")
        text = prometheus_metrics_text()
        self.assertIn("projectforge_http_requests_total", text)
        response = client.get("/api/v1/observability/prometheus")
        self.assertEqual(response.status_code, 200)
        self.assertIn("projectforge_http_requests_total", response.text)

    def test_jaeger_trace_export(self):
        client = TestClient(main.app)
        client.get("/health")
        payload = jaeger_trace_batch(10)
        self.assertIn("data", payload)
        response = client.get("/api/v1/observability/traces/jaeger")
        self.assertEqual(response.status_code, 200)

    def test_tenant_billing_quota(self):
        registry = TenantRegistry()
        tenant = registry.create(name="Billing Tenant", tier="starter", tenant_id="tenant_bill")
        billing = TenantBillingService(tenant_registry=registry)
        status = billing.quota_status(tenant.tenant_id)
        self.assertEqual(status["tier"], "starter")
        self.assertIn("max_projects", status["quotas"])

    def test_tenant_usage_store_records_requests(self):
        store = TenantUsageStore()
        store.record_api_request("tenant_a", 3)
        snapshot = store.snapshot("tenant_a")
        self.assertEqual(snapshot["api_requests"], 3)

    def test_tenant_billing_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/tenants/tenant_default/billing/quota")
        self.assertEqual(response.status_code, 200)
        self.assertIn("checks", response.json())

    def test_rotation_manifest_helper(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from rotate_airgap_gpg_key import generate_rotation_manifest

        manifest = generate_rotation_manifest(
            old_key_id="old@example.com",
            new_key_id="new@example.com",
            public_key_path=Path("release.pub.asc"),
        )
        self.assertEqual(manifest["new_key_id"], "new@example.com")
        self.assertIn("next_steps", manifest)


if __name__ == "__main__":
    unittest.main()
