import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings


class IntakeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = {
            "INTEGRATIONS_CONNECTION_ROOT": settings.INTEGRATIONS_CONNECTION_ROOT,
            "COMPLIANCE_PROFILE_ROOT": settings.COMPLIANCE_PROFILE_ROOT,
            "COMPLIANCE_AUDIT_ROOT": settings.COMPLIANCE_AUDIT_ROOT,
            "ENCRYPTION_KEY": settings.ENCRYPTION_KEY,
        }
        root = Path(self.temp_dir.name)
        settings.INTEGRATIONS_CONNECTION_ROOT = str(root / "connections")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "profiles")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")
        settings.ENCRYPTION_KEY = "test-key"

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        self.temp_dir.cleanup()

    def test_oauth_start_callback_status_and_health_flow(self):
        client = TestClient(main.app)

        start = client.post(
            "/api/v1/intake/connections/oauth/start",
            json={"connector_type": "google", "project_id": "api-int"},
        )
        self.assertEqual(start.status_code, 200)
        self.assertIn("authorization_url", start.json())
        state = start.json()["state"]

        callback = client.get(
            f"/api/v1/intake/oauth/google/callback?code=abc&state={state}&project_id=api-int"
        )
        self.assertEqual(callback.status_code, 200)
        self.assertNotIn("access_token", callback.json()["connection"]["summary"])

        status = client.get("/api/v1/intake/connections/api-int/google/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "connected")

        health = client.get("/api/v1/intake/connections/api-int/google/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["checks"]["token_present"])

    def test_api_key_and_mcp_endpoints(self):
        client = TestClient(main.app)

        jira = client.post(
            "/api/v1/intake/connections",
            json={
                "connector_type": "jira",
                "auth_data": {"api_key": "secret", "base_url": "https://jira.local"},
                "project_id": "api-key-project",
            },
        )
        self.assertEqual(jira.status_code, 200)
        self.assertNotIn("api_key", jira.json()["connection"]["summary"])

        mcp = client.post(
            "/api/v1/intake/connections",
            json={
                "connector_type": "mcp_server",
                "auth_data": {"server_url": "https://mcp.local"},
                "project_id": "api-key-project",
            },
        )
        self.assertEqual(mcp.status_code, 200)

        connections = client.get("/api/v1/intake/connections/api-key-project")
        self.assertEqual(len(connections.json()["connections"]), 2)

        tools = client.get("/api/v1/intake/connections/api-key-project/mcp/tools")
        self.assertEqual(tools.status_code, 200)
        self.assertEqual(tools.json()["tool_count"], 0)


if __name__ == "__main__":
    unittest.main()
