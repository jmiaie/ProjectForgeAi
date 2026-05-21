import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from core.config import settings
from graph.adapter import InMemoryGraphStore
from graph.builder import ProjectGraphBuilder
from storage.locus_adapter import LocusAdapter
from workbench.service import WorkbenchService


class WorkbenchTests(unittest.IsolatedAsyncioTestCase):
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

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        InMemoryGraphStore._graphs.clear()
        self.temp_dir.cleanup()

    async def test_workbench_returns_grounded_answer(self):
        manifest_dir = Path(settings.INGESTION_MANIFEST_ROOT) / "workbench"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "project_id": "workbench",
            "created_at": datetime.now(UTC).isoformat(),
            "files_processed": 1,
            "chunks_indexed": 1,
            "warnings": [],
            "documents": [
                {
                    "source": "plan.pdf",
                    "metadata": {"parser": "pdf", "source": "plan.pdf", "chunk_count": 1},
                    "warnings": [],
                    "chunks": [{"parser": "pdf", "source_hash": "abc", "chunk_index": 1}],
                }
            ],
            "storage": {},
            "session": {},
        }
        (manifest_dir / "latest.json").write_text(json.dumps(manifest))

        builder = ProjectGraphBuilder()
        builder.build_from_latest_manifest("workbench")

        locus = LocusAdapter("workbench")
        await locus.index_files(
            [{"source": "plan.pdf", "text": "Kickoff milestone on Monday", "metadata": {"parser": "pdf"}}]
        )

        service = WorkbenchService(graph_builder=builder)
        result = await service.query("workbench", "kickoff milestone")

        self.assertIn("Kickoff milestone", result["answer"])
        self.assertEqual(result["graph"]["sources"], ["plan.pdf"])
        self.assertEqual(len(result["context"]), 1)


if __name__ == "__main__":
    unittest.main()
