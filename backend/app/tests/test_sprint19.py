import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.config import settings
from fastapi.testclient import TestClient
from projects.registry import ProjectRegistry
from projects.service import PortfolioService
from tenancy.isolation import TenantIsolation
from tenancy.registry import TenantRegistry

import main


class Sprint19Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.TENANT_REGISTRY_ROOT = str(root / "tenants")
        settings.PROJECT_REGISTRY_ROOT = str(root / "projects")
        settings.DEFAULT_TENANT_ID = "tenant_default"
        settings.DEFAULT_PROJECT_ID = "proj_123"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tenant_register_and_status(self):
        client = TestClient(main.app)
        created = client.post("/api/v1/tenants/register", json={"name": "Acme Corp", "tier": "pro"})
        self.assertEqual(created.status_code, 200)
        tenant_id = created.json()["tenant"]["tenant_id"]

        status = client.get(f"/api/v1/tenants/{tenant_id}/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["tenant"]["name"], "Acme Corp")

    def test_tenant_isolation_scopes_project_registry(self):
        with patch.object(settings, "TENANT_ISOLATION_ENABLED", True):
            registry = TenantRegistry()
            tenant_a = registry.create(name="Tenant A", tenant_id="tenant_a")
            tenant_b = registry.create(name="Tenant B", tenant_id="tenant_b")
            TenantIsolation.ensure_tenant_dirs(tenant_a.tenant_id)
            TenantIsolation.ensure_tenant_dirs(tenant_b.tenant_id)

            service_a = PortfolioService(registry=ProjectRegistry(tenant_id=tenant_a.tenant_id))
            service_b = PortfolioService(registry=ProjectRegistry(tenant_id=tenant_b.tenant_id))

            project_a = service_a.create_project(name="Project A")
            project_b = service_b.create_project(name="Project B")

            listed_a = service_a.list_projects()
            listed_b = service_b.list_projects()
            ids_a = [item["project_id"] for item in listed_a["projects"]]
            ids_b = [item["project_id"] for item in listed_b["projects"]]
            self.assertIn(project_a.project_id, ids_a)
            self.assertNotIn(project_b.project_id, ids_a)
            self.assertIn(project_b.project_id, ids_b)

    def test_observability_metrics_endpoint(self):
        client = TestClient(main.app)
        client.get("/health")
        response = client.get("/api/v1/observability/metrics")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("metrics", payload)
        self.assertGreaterEqual(payload["metrics"].get("request_count", 0), 1)
        self.assertIn("X-Request-ID", client.get("/health").headers)

    def test_gpg_verify_mock(self):
        from core.bundle_gpg import verify_signature

        archive = Path(self.temp_dir.name) / "bundle.tar.gz"
        signature = Path(f"{archive}.asc")
        archive.write_bytes(b"bundle")
        signature.write_text("signed")

        with patch("core.bundle_gpg.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Good signature", stderr="")
            result = verify_signature(archive=archive, signature_path=signature)
        self.assertTrue(result["verified"])

    def test_list_tenants_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/tenants")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)


if __name__ == "__main__":
    unittest.main()
