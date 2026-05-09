import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings
from graph.adapter import InMemoryGraphStore, Neo4jGraphAdapter


class OrchestratorApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = {
            "INGESTION_MANIFEST_ROOT": settings.INGESTION_MANIFEST_ROOT,
            "ORCHESTRATION_RUN_ROOT": settings.ORCHESTRATION_RUN_ROOT,
            "LOCUS_STORE_ROOT": settings.LOCUS_STORE_ROOT,
            "OMPA_VAULT_ROOT": settings.OMPA_VAULT_ROOT,
        }
        root = Path(self.temp_dir.name)
        settings.INGESTION_MANIFEST_ROOT = str(root / "manifests")
        settings.ORCHESTRATION_RUN_ROOT = str(root / "runs")
        settings.LOCUS_STORE_ROOT = str(root / "locus")
        settings.OMPA_VAULT_ROOT = str(root / "vaults")
        InMemoryGraphStore._graphs.clear()
        Neo4jGraphAdapter._native_disabled_warning = "disabled for orchestrator API tests"

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        InMemoryGraphStore._graphs.clear()
        Neo4jGraphAdapter._native_disabled_warning = None
        self.temp_dir.cleanup()

    def test_orchestrator_endpoint_persists_run_status(self):
        message = EmailMessage()
        message["Subject"] = "Orchestrator Upload"
        message["From"] = "owner@example.com"
        message["To"] = "pm@example.com"
        message.set_content("Run the operating plan workflow.")

        client = TestClient(main.app)
        upload = client.post(
            "/api/v1/projects/upload",
            data={"project_id": "orch-api", "compliance": "standard"},
            files=[("files", ("orch.eml", message.as_bytes(), "message/rfc822"))],
        )
        self.assertEqual(upload.status_code, 200)

        run = client.post(
            "/api/v1/orchestrator/run",
            json={
                "project_id": "orch-api",
                "goal": "Create operating plan",
                "run_id": "run_api",
            },
        )
        self.assertEqual(run.status_code, 200)
        payload = run.json()
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(len(payload["steps"]), 5)

        status = client.get("/api/v1/projects/orch-api/orchestrator/status?run_id=run_api")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "completed")


if __name__ == "__main__":
    unittest.main()
