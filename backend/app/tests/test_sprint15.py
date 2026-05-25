import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from fastapi.testclient import TestClient
from spatial.service import SpatialService
from spatial.store import SpatialAssetStore, extract_coordinates

import main


class Sprint15Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.SPATIAL_ASSET_ROOT = str(root / "spatial")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "compliance")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_coordinates_from_properties(self):
        coords = extract_coordinates({"name": "Site A", "latitude": 37.77, "longitude": -122.42})
        self.assertEqual(coords, (37.77, -122.42, None))

    def test_register_and_list_spatial_assets(self):
        service = SpatialService()
        service.register_asset("proj-map", name="Crane pad", latitude=40.1, longitude=-74.2)
        listed = service.list_assets("proj-map")
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["assets"][0]["name"], "Crane pad")

    def test_sync_from_graph_indexes_geo_nodes(self):
        service = SpatialService()

        class FakeBuilder:
            def get_graph(self, project_id: str):
                return {
                    "graph": {
                        "nodes": [
                            {
                                "id": "node_1",
                                "label": "Milestone",
                                "properties": {
                                    "name": "Foundation pour",
                                    "lat": 37.78,
                                    "lon": -122.41,
                                },
                            },
                            {
                                "id": "node_2",
                                "label": "Task",
                                "properties": {"name": "No coords"},
                            },
                        ]
                    }
                }

        service.graph_builder = FakeBuilder()
        result = service.sync_from_graph("proj-map")
        self.assertEqual(result["synced"], 1)
        map_view = service.map_view("proj-map")
        self.assertEqual(map_view["marker_count"], 1)
        self.assertIsNotNone(map_view["bounds"])

    def test_spatial_api_register_and_map(self):
        client = TestClient(main.app)
        created = client.post(
            "/api/v1/projects/proj_123/spatial/assets",
            json={
                "name": "Gate A",
                "latitude": 37.775,
                "longitude": -122.418,
                "asset_type": "site",
            },
        )
        self.assertEqual(created.status_code, 200)
        map_view = client.get("/api/v1/projects/proj_123/spatial/map")
        self.assertEqual(map_view.status_code, 200)
        self.assertGreaterEqual(map_view.json()["marker_count"], 1)

    def test_rtk_status_reports_asset_count(self):
        store = SpatialAssetStore()
        service = SpatialService(store=store)
        service.register_asset("rtk-proj", name="Anchor", latitude=1.0, longitude=2.0)
        status = service.rtk_status("rtk-proj")
        self.assertEqual(status["asset_count"], 1)
        self.assertIn("rtk_cli_available", status)


if __name__ == "__main__":
    unittest.main()
