import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings
from graph.adapter import InMemoryGraphStore
from storage.locus_adapter import LocusAdapter


class WorkbenchApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.original = {
            "INGESTION_MANIFEST_ROOT": settings.INGESTION_MANIFEST_ROOT,
            "LOCUS_STORE_ROOT": settings.LOCUS_STORE_ROOT,
        }
        settings.INGESTION_MANIFEST_ROOT = str(root / "ingestion")
        settings.LOCUS_STORE_ROOT = str(root / "locus")
        InMemoryGraphStore._graphs.clear()
        self.client = TestClient(main.app)

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        InMemoryGraphStore._graphs.clear()
        self.temp_dir.cleanup()

    async def test_workbench_query_endpoint(self):
        locus = LocusAdapter("workbench-api")
        await locus.index_files(
            [{"source": "notes.txt", "text": "Project kickoff next week", "metadata": {"parser": "txt"}}]
        )

        response = self.client.post(
            "/api/v1/projects/workbench-api/workbench/query",
            json={"query": "kickoff"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("kickoff", body["answer"].lower())
        self.assertEqual(len(body["context"]), 1)


if __name__ == "__main__":
    unittest.main()
