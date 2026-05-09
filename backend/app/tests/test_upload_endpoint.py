import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.config import settings


class UploadEndpointTests(unittest.TestCase):
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

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        self.temp_dir.cleanup()

    def test_upload_endpoint_ingests_email_and_writes_manifest(self):
        message = EmailMessage()
        message["Subject"] = "Upload"
        message["From"] = "owner@example.com"
        message["To"] = "pm@example.com"
        message.set_content("Uploaded project instruction.")

        client = TestClient(main.app)
        response = client.post(
            "/api/v1/projects/upload",
            data={"project_id": "upload-test", "compliance": "standard"},
            files=[("files", ("instruction.eml", message.as_bytes(), "message/rfc822"))],
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ingestion = payload["ingestion"]
        self.assertEqual(payload["project_id"], "upload-test")
        self.assertEqual(ingestion["files_processed"], 1)
        self.assertEqual(ingestion["chunks_indexed"], 1)
        self.assertTrue(Path(ingestion["manifest"]["path"]).exists())


if __name__ == "__main__":
    unittest.main()
