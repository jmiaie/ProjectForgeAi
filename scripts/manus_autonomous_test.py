#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Callable
from uuid import uuid4

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app


@dataclass
class StepResult:
    name: str
    success: bool
    detail: str


class AutonomousRunner:
    def __init__(self) -> None:
        self.client = TestClient(app)
        self.project_id = f"proj_manus_{uuid4().hex[:8]}"
        self.oauth_state: str | None = None
        self.workflow_job_id: str | None = None

    @staticmethod
    def _pdf_bytes() -> bytes:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buffer = BytesIO()
        writer.write(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def _step(self, name: str, fn: Callable[[], tuple[bool, str]]) -> StepResult:
        try:
            success, detail = fn()
            return StepResult(name=name, success=success, detail=detail)
        except Exception as exc:  # pragma: no cover - defensive path
            return StepResult(name=name, success=False, detail=f"exception: {exc}")

    def run(self) -> list[StepResult]:
        return [
            self._step("health", self.step_health),
            self._step("recommended_connectors", self.step_recommended),
            self._step("oauth_start", self.step_oauth_start),
            self._step("oauth_callback", self.step_oauth_callback),
            self._step("api_key_connect", self.step_api_key_connect),
            self._step("mcp_connect", self.step_mcp_connect),
            self._step("project_create_ingest", self.step_create_project),
            self._step("project_orchestrate", self.step_orchestrate),
            self._step("workflow_job_create", self.step_workflow_job_create),
            self._step("workflow_job_run", self.step_workflow_job_run),
            self._step("report_generate", self.step_report_generate),
            self._step("workflow_tick", self.step_workflow_tick),
            self._step("graph_summary", self.step_graph_summary),
            self._step("dashboard", self.step_dashboard),
            self._step("audit_events", self.step_audit_events),
        ]

    def step_health(self) -> tuple[bool, str]:
        response = self.client.get("/health")
        ok = response.status_code == 200 and response.json().get("status") == "healthy"
        return ok, f"status_code={response.status_code}"

    def step_recommended(self) -> tuple[bool, str]:
        response = self.client.get("/api/v1/intake/recommended", params={"project_id": self.project_id})
        connectors = response.json().get("connectors", []) if response.status_code == 200 else []
        ok = response.status_code == 200 and len(connectors) >= 5
        return ok, f"connectors={len(connectors)}"

    def step_oauth_start(self) -> tuple[bool, str]:
        response = self.client.post(
            "/api/v1/intake/oauth/start",
            json={
                "connector_type": "github",
                "project_id": self.project_id,
                "redirect_uri": "https://app.projectforge.ai/settings/connections/callback",
            },
        )
        payload = response.json() if response.status_code == 200 else {}
        self.oauth_state = payload.get("state")
        ok = response.status_code == 200 and bool(self.oauth_state)
        return ok, f"state_present={bool(self.oauth_state)}"

    def step_oauth_callback(self) -> tuple[bool, str]:
        if not self.oauth_state:
            return False, "missing oauth state"
        response = self.client.post(
            "/api/v1/intake/oauth/callback",
            json={
                "connector_type": "github",
                "project_id": self.project_id,
                "state": self.oauth_state,
                "code": "manus-demo-code",
                "redirect_uri": "https://app.projectforge.ai/settings/connections/callback",
            },
        )
        payload = response.json() if response.status_code == 200 else {}
        ok = response.status_code == 200 and payload.get("status") == "connected"
        return ok, f"status={payload.get('status')}"

    def step_api_key_connect(self) -> tuple[bool, str]:
        response = self.client.post(
            "/api/v1/intake/api-key",
            json={"connector_type": "jira", "project_id": self.project_id, "api_key": "jira_abcdef123456"},
        )
        payload = response.json() if response.status_code == 200 else {}
        ok = response.status_code == 200 and payload.get("status") == "connected"
        return ok, f"status={payload.get('status')}"

    def step_mcp_connect(self) -> tuple[bool, str]:
        response = self.client.post(
            "/api/v1/intake/mcp",
            json={
                "connector_type": "mcp_server",
                "project_id": self.project_id,
                "server_url": "https://example-mcp-server.local",
            },
        )
        payload = response.json() if response.status_code == 200 else {}
        status = payload.get("status")
        ok = response.status_code == 200 and status in {"connected", "error"}
        return ok, f"status={status}"

    def step_create_project(self) -> tuple[bool, str]:
        files = [
            ("files", ("manus.pdf", self._pdf_bytes(), "application/pdf")),
            ("files", ("notes.eml", b"Subject: Manus\n\nAutonomous ingestion run", "message/rfc822")),
        ]
        response = self.client.post("/api/v1/projects/", files=files)
        payload = response.json() if response.status_code == 200 else {}
        ok = response.status_code == 200 and payload.get("status") == "orchestrated"
        return ok, f"files={payload.get('ingestion', {}).get('files')}"

    def step_orchestrate(self) -> tuple[bool, str]:
        response = self.client.post(f"/api/v1/projects/{self.project_id}/orchestrate")
        payload = response.json() if response.status_code == 200 else {}
        states = payload.get("orchestration", {}).get("states_visited", [])
        ok = response.status_code == 200 and "templates_generated" in states
        return ok, f"states={len(states)}"

    def step_workflow_job_create(self) -> tuple[bool, str]:
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/workflows/jobs",
            json={
                "name": "Manus Weekly Automation",
                "job_type": "weekly_status_report",
                "schedule_type": "hourly",
                "interval_minutes": 1,
                "payload": {"source": "manus"},
            },
        )
        payload = response.json() if response.status_code == 200 else {}
        self.workflow_job_id = payload.get("job", {}).get("job_id")
        ok = response.status_code == 200 and bool(self.workflow_job_id)
        return ok, f"job_id_present={bool(self.workflow_job_id)}"

    def step_workflow_job_run(self) -> tuple[bool, str]:
        if not self.workflow_job_id:
            return False, "missing workflow job id"
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/workflows/jobs/{self.workflow_job_id}/run",
            json={},
        )
        payload = response.json() if response.status_code == 200 else {}
        ok = response.status_code == 200 and payload.get("status") == "executed"
        return ok, f"status={payload.get('status')}"

    def step_report_generate(self) -> tuple[bool, str]:
        response = self.client.post(f"/api/v1/projects/{self.project_id}/reports/weekly-status")
        payload = response.json() if response.status_code == 200 else {}
        report_id = payload.get("report", {}).get("report_id")
        ok = response.status_code == 200 and payload.get("status") == "generated" and bool(report_id)
        return ok, f"report_id_present={bool(report_id)}"

    def step_workflow_tick(self) -> tuple[bool, str]:
        create_due = self.client.post(
            f"/api/v1/projects/{self.project_id}/workflows/jobs",
            json={
                "name": "Due Digest",
                "job_type": "audit_digest",
                "schedule_type": "once",
                "run_at": "2000-01-01T00:00:00+00:00",
            },
        )
        if create_due.status_code != 200:
            return False, f"create_due_status={create_due.status_code}"

        tick = self.client.post(f"/api/v1/projects/{self.project_id}/workflows/tick")
        payload = tick.json() if tick.status_code == 200 else {}
        executed = payload.get("executed", 0)
        ok = tick.status_code == 200 and executed >= 1
        return ok, f"executed={executed}"

    def step_graph_summary(self) -> tuple[bool, str]:
        response = self.client.get(f"/api/v1/projects/{self.project_id}/graph/summary")
        payload = response.json() if response.status_code == 200 else {}
        ok = response.status_code == 200 and payload.get("status") == "ok"
        return ok, f"nodes={payload.get('nodes', 0)}"

    def step_dashboard(self) -> tuple[bool, str]:
        response = self.client.get(f"/api/v1/projects/{self.project_id}/dashboard")
        payload = response.json() if response.status_code == 200 else {}
        metrics = payload.get("metrics", {})
        ok = response.status_code == 200 and bool(metrics)
        return ok, f"metrics_keys={len(metrics.keys())}"

    def step_audit_events(self) -> tuple[bool, str]:
        response = self.client.get(f"/api/v1/projects/{self.project_id}/audit-events")
        payload = response.json() if response.status_code == 200 else {}
        events = payload.get("events", [])
        ok = response.status_code == 200 and len(events) >= 3
        return ok, f"events={len(events)}"


def main() -> int:
    runner = AutonomousRunner()
    results = runner.run()

    failures = 0
    for result in results:
        marker = "PASS" if result.success else "FAIL"
        print(f"[{marker}] {result.name}: {result.detail}")
        if not result.success:
            failures += 1

    print(f"\nCompleted {len(results)} checks with {failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
