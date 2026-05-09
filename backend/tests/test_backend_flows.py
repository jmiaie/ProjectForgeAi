from __future__ import annotations

import unittest
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app


class BackendFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    @staticmethod
    def _project_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"

    @staticmethod
    def _pdf_bytes() -> bytes:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buffer = BytesIO()
        writer.write(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def test_project_creation_ingestion_orchestration_graph(self) -> None:
        files = [
            ("files", ("spec.pdf", self._pdf_bytes(), "application/pdf")),
            ("files", ("notes.eml", b"Subject: Sprint\n\nRun ingestion checks.", "message/rfc822")),
        ]
        response = self.client.post("/api/v1/projects/", files=files)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["status"], "orchestrated")
        self.assertEqual(payload["ingestion"]["files"], 2)
        self.assertGreaterEqual(payload["ingestion"]["chunks_indexed"], 2)
        self.assertIn("templates_generated", payload["orchestration"]["states_visited"])
        self.assertGreater(payload["graph"]["nodes"], 0)
        self.assertGreater(payload["graph"]["edges"], 0)

    def test_intake_oauth_api_key_mcp_and_connection_list(self) -> None:
        project_id = self._project_id("proj_intake")

        recommended = self.client.get("/api/v1/intake/recommended", params={"project_id": project_id})
        self.assertEqual(recommended.status_code, 200)
        self.assertGreaterEqual(len(recommended.json().get("connectors", [])), 5)

        oauth_start = self.client.post(
            "/api/v1/intake/oauth/start",
            json={
                "connector_type": "github",
                "project_id": project_id,
                "redirect_uri": "https://app.projectforge.ai/settings/connections/callback",
            },
        )
        self.assertEqual(oauth_start.status_code, 200)
        oauth_payload = oauth_start.json()
        self.assertEqual(oauth_payload["status"], "authorization_required")
        self.assertTrue(oauth_payload["state"])

        oauth_callback = self.client.post(
            "/api/v1/intake/oauth/callback",
            json={
                "connector_type": "github",
                "project_id": project_id,
                "state": oauth_payload["state"],
                "code": "demo-oauth-code",
                "redirect_uri": "https://app.projectforge.ai/settings/connections/callback",
            },
        )
        self.assertEqual(oauth_callback.status_code, 200)
        self.assertEqual(oauth_callback.json()["status"], "connected")

        api_key = self.client.post(
            "/api/v1/intake/api-key",
            json={"connector_type": "jira", "project_id": project_id, "api_key": "jira_key_1234567890"},
        )
        self.assertEqual(api_key.status_code, 200)
        self.assertEqual(api_key.json()["status"], "connected")

        mcp = self.client.post(
            "/api/v1/intake/mcp",
            json={
                "connector_type": "mcp_server",
                "project_id": project_id,
                "server_url": "https://example-mcp-server.local",
                "token": "example-token",
            },
        )
        self.assertEqual(mcp.status_code, 200)
        self.assertIn(mcp.json()["status"], {"connected", "error"})

        connections = self.client.get("/api/v1/intake/connections", params={"project_id": project_id})
        self.assertEqual(connections.status_code, 200)
        self.assertGreaterEqual(len(connections.json().get("connections", [])), 3)

    def test_dashboard_and_audit_surface(self) -> None:
        project_id = self._project_id("proj_dash")

        compliance = self.client.post(
            f"/api/v1/projects/{project_id}/compliance",
            json={"category": "soc2"},
        )
        self.assertEqual(compliance.status_code, 200)

        api_key = self.client.post(
            "/api/v1/intake/api-key",
            json={"connector_type": "jira", "project_id": project_id, "api_key": "jira_dash_0987654321"},
        )
        self.assertEqual(api_key.status_code, 200)

        orchestrate = self.client.post(f"/api/v1/projects/{project_id}/orchestrate")
        self.assertEqual(orchestrate.status_code, 200)

        dashboard = self.client.get(f"/api/v1/projects/{project_id}/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        dashboard_payload = dashboard.json()
        self.assertEqual(dashboard_payload["status"], "ok")
        self.assertIn("metrics", dashboard_payload)
        self.assertIn("workflow", dashboard_payload)
        self.assertIn("connections", dashboard_payload)
        self.assertIn("recent_events", dashboard_payload)
        self.assertIn("state_store_backend", dashboard_payload)
        self.assertIn(dashboard_payload["state_store_backend"], {"postgres", "in_memory"})
        self.assertGreaterEqual(dashboard_payload["metrics"]["workflow_steps_completed"], 1)

        audit = self.client.get(f"/api/v1/projects/{project_id}/audit-events")
        self.assertEqual(audit.status_code, 200)
        events = audit.json().get("events", [])
        self.assertGreaterEqual(len(events), 2)
        event_types = {event["event_type"] for event in events}
        self.assertIn("compliance_profile_updated", event_types)
        self.assertIn("integration_connected", event_types)

    def test_workflow_job_registry_and_reports(self) -> None:
        project_id = self._project_id("proj_workflow")

        create_job = self.client.post(
            f"/api/v1/projects/{project_id}/workflows/jobs",
            json={
                "name": "Hourly Weekly Report",
                "job_type": "weekly_status_report",
                "schedule_type": "hourly",
                "interval_minutes": 1,
                "payload": {"channel": "email"},
            },
        )
        self.assertEqual(create_job.status_code, 200)
        job = create_job.json()["job"]
        job_id = job["job_id"]

        jobs = self.client.get(f"/api/v1/projects/{project_id}/workflows/jobs")
        self.assertEqual(jobs.status_code, 200)
        self.assertGreaterEqual(len(jobs.json().get("jobs", [])), 1)

        run_job = self.client.post(
            f"/api/v1/projects/{project_id}/workflows/jobs/{job_id}/run",
            json={},
        )
        self.assertEqual(run_job.status_code, 200)
        self.assertEqual(run_job.json()["status"], "executed")

        runs = self.client.get(f"/api/v1/projects/{project_id}/workflows/runs")
        self.assertEqual(runs.status_code, 200)
        self.assertGreaterEqual(len(runs.json().get("runs", [])), 1)

        report = self.client.post(f"/api/v1/projects/{project_id}/reports/weekly-status")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()["status"], "generated")

        schedule = self.client.post(
            f"/api/v1/projects/{project_id}/reports/weekly-status/schedule",
            json={"name": "Weekly Report Schedule", "schedule_type": "weekly"},
        )
        self.assertEqual(schedule.status_code, 200)
        self.assertEqual(schedule.json()["status"], "scheduled")

        due_job = self.client.post(
            f"/api/v1/projects/{project_id}/workflows/jobs",
            json={
                "name": "Past Due Digest",
                "job_type": "audit_digest",
                "schedule_type": "once",
                "run_at": "2000-01-01T00:00:00+00:00",
            },
        )
        self.assertEqual(due_job.status_code, 200)

        tick = self.client.post(f"/api/v1/projects/{project_id}/workflows/tick")
        self.assertEqual(tick.status_code, 200)
        self.assertGreaterEqual(tick.json().get("executed", 0), 1)

        reports = self.client.get(f"/api/v1/projects/{project_id}/reports")
        self.assertEqual(reports.status_code, 200)
        self.assertGreaterEqual(len(reports.json().get("reports", [])), 2)


if __name__ == "__main__":
    unittest.main()
