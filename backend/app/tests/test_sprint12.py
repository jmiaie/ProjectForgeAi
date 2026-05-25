import tempfile
import unittest
from pathlib import Path

from core.config import settings
from fastapi.testclient import TestClient
from projects.registry import ProjectRegistry
from projects.service import PortfolioService

import main


class Sprint12Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.PROJECT_REGISTRY_ROOT = str(root / "projects")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "compliance")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")
        settings.DEFAULT_PROJECT_ID = "proj_123"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registry_seeds_default_project(self):
        registry = ProjectRegistry()
        projects = registry.list_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].project_id, "proj_123")

    def test_create_and_list_projects(self):
        service = PortfolioService()
        created = service.create_project(name="Alpha Build", compliance="legal", tier="pro")
        listed = service.list_projects()
        ids = [project["project_id"] for project in listed["projects"]]
        self.assertIn(created.project_id, ids)
        self.assertEqual(created.compliance, "legal")
        self.assertEqual(created.tier, "pro")

    def test_portfolio_summary_aggregates_graph_counts(self):
        service = PortfolioService()
        service.create_project(name="Beta", compliance="standard")
        summary = service.portfolio_summary()
        self.assertGreaterEqual(summary["totals"]["projects"], 2)
        self.assertIn("projects", summary)

    def test_archive_project(self):
        service = PortfolioService()
        created = service.create_project(name="Archive Me")
        archived = service.archive_project(created.project_id)
        self.assertEqual(archived.status, "archived")
        active = service.list_projects(include_archived=False)
        active_ids = [project["project_id"] for project in active["projects"]]
        self.assertNotIn(created.project_id, active_ids)

    def test_register_project_api(self):
        client = TestClient(main.app)
        response = client.post(
            "/api/v1/projects/register",
            json={"name": "API Project", "compliance": "soc2", "tier": "enterprise"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "created")
        self.assertEqual(payload["project"]["compliance"], "soc2")

    def test_portfolio_summary_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/portfolio/summary")
        self.assertEqual(response.status_code, 200)
        self.assertIn("totals", response.json())
        self.assertIn("projects", response.json())

    def test_list_projects_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/projects")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)


if __name__ == "__main__":
    unittest.main()
