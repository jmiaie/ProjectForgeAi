import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings


class ComplianceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = {
            "COMPLIANCE_PROFILE_ROOT": settings.COMPLIANCE_PROFILE_ROOT,
            "COMPLIANCE_AUDIT_ROOT": settings.COMPLIANCE_AUDIT_ROOT,
        }
        root = Path(self.temp_dir.name)
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "profiles")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        self.temp_dir.cleanup()

    def test_profile_and_audit_endpoints(self):
        client = TestClient(main.app)

        set_profile = client.post(
            "/api/v1/projects/compliance-api/compliance/profile",
            json={"category": "hipaa"},
        )
        self.assertEqual(set_profile.status_code, 200)
        self.assertEqual(set_profile.json()["category"], "hipaa")

        profile = client.get("/api/v1/projects/compliance-api/compliance/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertFalse(profile.json()["allow_memory_writes"])

        audit = client.get("/api/v1/projects/compliance-api/compliance/audit")
        self.assertEqual(audit.status_code, 200)
        self.assertTrue(any(event["action"] == "profile_set" for event in audit.json()["events"]))

    def test_restricted_profile_blocks_external_write(self):
        client = TestClient(main.app)
        client.post("/api/v1/projects/blocked/compliance/profile", json={"category": "hipaa"})

        response = client.post(
            "/api/v1/intake/connections",
            json={
                "connector_type": "google",
                "auth_data": {"code": "abc"},
                "project_id": "blocked",
            },
        )

        self.assertEqual(response.status_code, 403)
        audit = client.get("/api/v1/projects/blocked/compliance/audit")
        self.assertTrue(
            any(event["action"] == "external_write" and not event["allowed"] for event in audit.json()["events"])
        )


if __name__ == "__main__":
    unittest.main()
