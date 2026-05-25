import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from core.config import settings
from ingestion.parsers.common.cad_bim import parse_dwg, parse_ifc
from ingestion.parsers.common.codebase import parse_code_archive
from ingestion.pipeline import IngestionPipeline

import main


IFC_SAMPLE = b"""ISO-10303-21;
HEADER;
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('guid',$,$,$,$,$,$,$,$);
#2=IFCWALL('guid',$,$,$,$,$,$,$,$);
ENDSEC;
END-ISO-10303-21;
"""


class Sprint13Tests(unittest.TestCase):
    def test_ifc_parser_extracts_schema_and_entities(self):
        parsed = parse_ifc(io.BytesIO(IFC_SAMPLE), filename="sample.ifc")
        self.assertEqual(parsed.metadata["parser"], "cad_bim_ifc")
        self.assertEqual(parsed.metadata["schema"], "IFC4")
        self.assertGreaterEqual(parsed.metadata["entity_count"], 2)
        self.assertIn("IFCWALL", parsed.chunks[0].text)

    def test_dwg_parser_returns_metadata_stub(self):
        parsed = parse_dwg(io.BytesIO(b"AC1032\x00metadata"), filename="plan.dwg")
        self.assertEqual(parsed.metadata["parser"], "cad_bim_dwg")
        self.assertEqual(parsed.metadata["chunk_count"], 1)
        self.assertTrue(parsed.warnings)

    def test_codebase_zip_indexes_source_files(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("src/main.py", "def run():\n    return 'ok'\n")
            archive.writestr("README.md", "# Demo repo")
        parsed = parse_code_archive(io.BytesIO(buffer.getvalue()), filename="repo.zip")
        self.assertEqual(parsed.metadata["parser"], "codebase")
        self.assertEqual(parsed.metadata["chunk_count"], 2)
        self.assertIn("def run", parsed.chunks[0].text)

    def test_pipeline_routes_ifc_and_zip(self):
        import asyncio

        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                settings.INGESTION_MANIFEST_ROOT = str(Path(temp_dir) / "manifests")
                settings.LOCUS_STORE_ROOT = str(Path(temp_dir) / "locus")
                settings.OMPA_VAULT_ROOT = str(Path(temp_dir) / "vaults")

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as archive:
                    archive.writestr("app.py", "print('hello')")

                class Upload:
                    filename = "repo.zip"

                    def __init__(self, data):
                        self.file = io.BytesIO(data)

                pipeline = IngestionPipeline()
                result = await pipeline.process_files("cad-code", [Upload(zip_buffer.getvalue())])
                self.assertEqual(result["files_processed"], 1)
                self.assertEqual(result["chunks_indexed"], 1)

        asyncio.run(run())

    def test_database_snapshot_api_with_mock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings.PROJECT_REGISTRY_ROOT = str(root / "projects")
            settings.INGESTION_MANIFEST_ROOT = str(root / "manifests")
            settings.LOCUS_STORE_ROOT = str(root / "locus")
            settings.OMPA_VAULT_ROOT = str(root / "vaults")
            settings.COMPLIANCE_PROFILE_ROOT = str(root / "compliance")
            settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")

            client = TestClient(main.app)
            client.post(
                "/api/v1/projects/register",
                json={"name": "DB Intake", "compliance": "standard"},
            )

            mock_cursor = MagicMock()
            mock_cursor.fetchall.side_effect = [
                [("tasks",), ("users",)],
                [("id", "integer", "NO"), ("name", "text", "YES")],
                [("id", "integer", "NO"), ("email", "text", "NO")],
                [],
            ]
            mock_conn = MagicMock()
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

            with patch("psycopg.connect", return_value=mock_conn):
                response = client.post(
                    "/api/v1/projects/db-intake/ingestion/database-snapshot",
                    json={"db_schema": "public", "connection_uri": "postgresql://test"},
                )
            self.assertEqual(response.status_code, 404)

            listed = client.get("/api/v1/projects")
            project_id = listed.json()["projects"][0]["project_id"]
            with patch("psycopg.connect", return_value=mock_conn):
                response = client.post(
                    f"/api/v1/projects/{project_id}/ingestion/database-snapshot",
                    json={"db_schema": "public", "connection_uri": "postgresql://test"},
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "snapshot_ingested")


if __name__ == "__main__":
    unittest.main()
