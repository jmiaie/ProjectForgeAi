from typing import Any

from graph.builder import ProjectGraphBuilder
from spatial.store import SpatialAsset, SpatialAssetStore, extract_coordinates
from storage.rtk_adapter import RTKAdapter


class SpatialService:
    def __init__(
        self,
        store: SpatialAssetStore | None = None,
        graph_builder: ProjectGraphBuilder | None = None,
    ):
        self.store = store or SpatialAssetStore()
        self.graph_builder = graph_builder or ProjectGraphBuilder()

    def list_assets(self, project_id: str) -> dict[str, Any]:
        assets = self.store.list_assets(project_id)
        return {"project_id": project_id, "count": len(assets), "assets": [a.as_dict() for a in assets]}

    def register_asset(
        self,
        project_id: str,
        *,
        name: str,
        latitude: float,
        longitude: float,
        altitude: float | None = None,
        asset_type: str = "site",
        graph_node_id: str | None = None,
        properties: dict | None = None,
    ) -> SpatialAsset:
        asset = SpatialAsset(
            project_id=project_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            asset_type=asset_type,
            graph_node_id=graph_node_id,
            source="manual",
            properties=properties or {},
        )
        return self.store.upsert(asset)

    def sync_from_graph(self, project_id: str) -> dict[str, Any]:
        graph_payload = self.graph_builder.get_graph(project_id)
        graph = graph_payload.get("graph", {})
        synced = 0
        skipped = 0

        for node in graph.get("nodes", []):
            coords = extract_coordinates(node.get("properties", {}))
            if coords is None:
                skipped += 1
                continue
            lat, lon, alt = coords
            name = str(node.get("properties", {}).get("name") or node.get("label") or node.get("id"))
            asset = SpatialAsset(
                project_id=project_id,
                name=name,
                latitude=lat,
                longitude=lon,
                altitude=alt,
                asset_type=str(node.get("label", "node")).lower(),
                graph_node_id=node.get("id"),
                source="graph_sync",
                properties={"label": node.get("label"), **node.get("properties", {})},
            )
            self.store.upsert(asset)
            synced += 1

        return {
            "project_id": project_id,
            "synced": synced,
            "skipped": skipped,
            "total_assets": len(self.store.list_assets(project_id)),
        }

    def map_view(self, project_id: str) -> dict[str, Any]:
        assets = self.store.list_assets(project_id)
        markers = [
            {
                "asset_id": asset.asset_id,
                "name": asset.name,
                "latitude": asset.latitude,
                "longitude": asset.longitude,
                "altitude": asset.altitude,
                "asset_type": asset.asset_type,
                "graph_node_id": asset.graph_node_id,
                "source": asset.source,
            }
            for asset in assets
        ]
        bounds = _compute_bounds(markers)
        return {
            "project_id": project_id,
            "marker_count": len(markers),
            "bounds": bounds,
            "markers": markers,
        }

    def rtk_status(self, project_id: str) -> dict[str, Any]:
        adapter = RTKAdapter(project_id=project_id, store=self.store)
        return adapter.status()


def _compute_bounds(markers: list[dict[str, Any]]) -> dict[str, float] | None:
    if not markers:
        return None
    lats = [marker["latitude"] for marker in markers]
    lons = [marker["longitude"] for marker in markers]
    padding = 0.001
    return {
        "min_lat": min(lats) - padding,
        "max_lat": max(lats) + padding,
        "min_lon": min(lons) - padding,
        "max_lon": max(lons) + padding,
    }
