import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings
from graph.adapter import InMemoryGraphStore
from graph.builder import ProjectGraphBuilder
from storage.locus_adapter import InMemoryLocusEngine, LocusAdapter


class GraphEnrichmentApiTests(unittest.IsolatedAsyncioTestCase):
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
        InMemoryLocusEngine._stores.clear()
        self.client = TestClient(main.app)

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        InMemoryGraphStore._graphs.clear()
        InMemoryLocusEngine._stores.clear()
        self.temp_dir.cleanup()

    async def test_graph_enrich_endpoint(self):
        manifest_dir = Path(settings.INGESTION_MANIFEST_ROOT) / "enrich-api"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "project_id": "enrich-api",
            "created_at": datetime.now(UTC).isoformat(),
            "files_processed": 1,
            "chunks_indexed": 1,
            "warnings": [],
            "documents": [
                {
                    "source": "notes.txt",
                    "metadata": {"parser": "txt", "source": "notes.txt", "source_hash": "hash1", "chunk_count": 1},
                    "warnings": [],
                    "chunks": [{"parser": "txt", "source_hash": "hash1", "chunk_index": 1}],
                }
            ],
            "storage": {},
            "session": {},
        }
        (manifest_dir / "latest.json").write_text(json.dumps(manifest))
        ProjectGraphBuilder().build_from_latest_manifest("enrich-api")

        locus = LocusAdapter("enrich-api")
        await locus.index_files(
            [
                {
                    "source": "notes.txt",
                    "text": "Kickoff milestone Monday\nTask: confirm vendors",
                    "metadata": {"source_hash": "hash1", "chunk_index": 1, "source": "notes.txt"},
                }
            ]
        )

        response = self.client.post(
            "/api/v1/projects/enrich-api/graph/enrich",
            json={"use_llm": False},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["facts_extracted"], 0)
        self.assertGreater(body["node_count"], 3)


if __name__ == "__main__":
    unittest.main()
