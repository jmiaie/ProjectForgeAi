import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from fastapi.testclient import TestClient

import main


class Sprint18Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_security_headers_when_hardened(self):
        with patch.object(settings, "PRODUCTION_HARDENING", True):
            client = TestClient(main.app)
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("Strict-Transport-Security", response.headers)

    def test_deploy_status_endpoint(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/deploy/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("production_hardening", payload)
        self.assertIn("build_info", payload)

    def test_build_and_apply_airgap_bundle(self):
        workspace = Path(__file__).resolve().parents[3]
        sys_path = str(workspace / "scripts")
        import sys

        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        from apply_airgap_bundle import apply_bundle
        from build_airgap_bundle import build_bundle

        output_dir = self.root / "bundles"
        archive = build_bundle(output_dir=output_dir, version="14.0.0-test", skip_wheels=True)
        self.assertTrue(archive.exists())

        target = self.root / "install"
        target.mkdir()
        for name in ("backend", "frontend", "deploy", "scripts", "requirements.txt", "docker-compose.yml"):
            src = workspace / name
            if src.is_dir():
                shutil.copytree(src, target / name, dirs_exist_ok=True)
            elif src.exists():
                shutil.copy2(src, target / name)

        result = apply_bundle(archive=archive, target_dir=target, install_wheels=False)
        self.assertEqual(result["version"], "14.0.0-test")
        self.assertTrue((target / "BUILD_INFO.json").exists())

        with tarfile.open(archive, "r:gz") as tar:
            names = tar.getnames()
        self.assertTrue(any(name.endswith("MANIFEST.json") for name in names))


if __name__ == "__main__":
    unittest.main()
