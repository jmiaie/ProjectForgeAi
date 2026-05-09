import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from core.config import settings
from ingestion.pipeline import IngestionPipeline
from storage.locus_adapter import LocusAdapter
from storage.ompa_adapter import OmpaAdapter


class StorageIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original = {
            "LOCUS_SOURCE_PATH": settings.LOCUS_SOURCE_PATH,
            "LOCUS_ENGINE": settings.LOCUS_ENGINE,
            "LOCUS_STORE_ROOT": settings.LOCUS_STORE_ROOT,
            "OMPA_SOURCE_PATH": settings.OMPA_SOURCE_PATH,
            "OMPA_ENGINE": settings.OMPA_ENGINE,
            "OMPA_VAULT_ROOT": settings.OMPA_VAULT_ROOT,
            "REQUIRE_NATIVE_LOCUS_OMPA": settings.REQUIRE_NATIVE_LOCUS_OMPA,
        }

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        sys.modules.pop("locus", None)
        sys.modules.pop("ompa", None)

    async def test_locus_and_ompa_load_from_source_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "locus.py").write_text(
                textwrap.dedent(
                    """
                    class LocusEngine:
                        def __init__(self, store_path):
                            self.store_path = store_path
                            self.chunks = []

                        def index(self, chunks):
                            self.chunks.extend(chunks)

                        def retrieve(self, query, limit=10):
                            return self.chunks[:limit]
                    """
                )
            )
            (root / "ompa.py").write_text(
                textwrap.dedent(
                    """
                    class Ompa:
                        def __init__(self, vault_path):
                            self.vault_path = vault_path
                            self.records = []

                        def classify(self, message):
                            self.records.append(message)

                        def session_start(self):
                            return {"status": "started", "vault_path": self.vault_path}
                    """
                )
            )

            settings.LOCUS_SOURCE_PATH = str(root)
            settings.OMPA_SOURCE_PATH = str(root)
            settings.LOCUS_STORE_ROOT = str(root / "locus-stores")
            settings.OMPA_VAULT_ROOT = str(root / "ompa-vaults")
            settings.REQUIRE_NATIVE_LOCUS_OMPA = True

            locus = LocusAdapter("native")
            ompa = OmpaAdapter("native")

            self.assertTrue(locus.status()["native"])
            self.assertTrue(ompa.status()["native"])
            await locus.index_files([{"text": "hello"}])
            self.assertEqual(await locus.retrieve("hello"), [{"text": "hello"}])

            pipeline = IngestionPipeline()
            result = await pipeline.process_files("native", ["scope.pdf"])
            self.assertTrue(result["storage"]["native_ready"])
            self.assertEqual(result["files_processed"], 1)


if __name__ == "__main__":
    unittest.main()
