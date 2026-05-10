import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings


class AutomationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = {
            "AUTOMATION_WORKFLOW_ROOT": settings.AUTOMATION_WORKFLOW_ROOT,
            "ORCHESTRATION_RUN_ROOT": settings.ORCHESTRATION_RUN_ROOT,
            "COMPLIANCE_PROFILE_ROOT": settings.COMPLIANCE_PROFILE_ROOT,
            "COMPLIANCE_AUDIT_ROOT": settings.COMPLIANCE_AUDIT_ROOT,
        }
        root = Path(self.temp_dir.name)
        settings.AUTOMATION_WORKFLOW_ROOT = str(root / "automations")
        settings.ORCHESTRATION_RUN_ROOT = str(root / "runs")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "profiles")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        self.temp_dir.cleanup()

    def test_create_run_and_list_reminder_automation(self):
        client = TestClient(main.app)
        created = client.post(
            "/api/v1/projects/api-auto/automations",
            json={
                "type": "timed_reminder",
                "name": "Reminder",
                "payload": {"message": "Check submittals", "recipient": "pm@example.com"},
            },
        )

        self.assertEqual(created.status_code, 200)
        automation_id = created.json()["id"]

        run = client.post(f"/api/v1/projects/api-auto/automations/{automation_id}/run")
        self.assertEqual(run.status_code, 200)
        self.assertEqual(run.json()["status"], "completed")

        listed = client.get("/api/v1/projects/api-auto/automations")
        self.assertEqual(len(listed.json()["automations"]), 1)

        runs = client.get("/api/v1/projects/api-auto/automations/runs")
        self.assertEqual(len(runs.json()["runs"]), 1)

    def test_approval_gate_api_flow(self):
        client = TestClient(main.app)
        created = client.post(
            "/api/v1/projects/gate-api/automations",
            json={
                "type": "approval_gate",
                "name": "Approve report",
                "payload": {"message": "Release weekly report"},
            },
        )
        automation_id = created.json()["id"]

        blocked = client.post(f"/api/v1/projects/gate-api/automations/{automation_id}/run")
        self.assertEqual(blocked.json()["status"], "waiting_approval")

        approved = client.post(
            f"/api/v1/projects/gate-api/automations/{automation_id}/approve",
            json={"approved_by": "owner@example.com"},
        )
        self.assertEqual(approved.json()["approved_by"], "owner@example.com")

        completed = client.post(f"/api/v1/projects/gate-api/automations/{automation_id}/run")
        self.assertEqual(completed.json()["status"], "completed")

    def test_temporal_status_endpoint(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/automations/temporal/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "configured")


if __name__ == "__main__":
    unittest.main()
