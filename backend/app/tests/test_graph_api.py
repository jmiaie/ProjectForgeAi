import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings
from graph.adapter import InMemoryGraphStore, Neo4jGraphAdapter


class GraphApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = {
            "INGESTION_MANIFEST_ROOT": settings.INGESTION_MANIFEST_ROOT,
            "LOCUS_STORE_ROOT": settings.LOCUS_STORE_ROOT,
            "OMPA_VAULT_ROOT": settings.OMPA_VAULT_ROOT,
        }
        root = Path(self.temp_dir.name)
        settings.INGESTION_MANIFEST_ROOT = str(root / "manifests")
        settings.LOCUS_STORE_ROOT = str(root / "locus")
        settings.OMPA_VAULT_ROOT = str(root / "vaults")
        InMemoryGraphStore._graphs.clear()
        Neo4jGraphAdapter._native_disabled_warning = "disabled for graph API tests"

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        InMemoryGraphStore._graphs.clear()
        Neo4jGraphAdapter._native_disabled_warning = None
        self.temp_dir.cleanup()

    def test_upload_builds_project_graph(self):
        message = EmailMessage()
        message["Subject"] = "Graph Upload"
        message["From"] = "owner@example.com"
        message["To"] = "pm@example.com"
        message.set_content("Create graph nodes from this email.")

        client = TestClient(main.app)
        upload = client.post(
            "/api/v1/projects/upload",
            data={"project_id": "graph-api", "compliance": "standard"},
            files=[("files", ("graph.eml", message.as_bytes(), "message/rfc822"))],
        )

        self.assertEqual(upload.status_code, 200)
        payload = upload.json()
        self.assertEqual(payload["graph"]["node_count"], 3)
        self.assertEqual(payload["graph"]["edge_count"], 2)

        graph_response = client.get("/api/v1/projects/graph-api/graph")
        self.assertEqual(graph_response.status_code, 200)
        graph_payload = graph_response.json()
        self.assertEqual(graph_payload["node_count"], 3)
        self.assertEqual(graph_payload["edge_count"], 2)

        status_response = client.get("/api/v1/projects/graph-api/graph/status")
        self.assertTrue(status_response.json()["built"])


if __name__ == "__main__":
    unittest.main()
