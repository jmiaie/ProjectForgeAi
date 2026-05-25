import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from core.config import settings


class SpatialAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: f"asset_{uuid4().hex[:12]}")
    project_id: str
    name: str
    latitude: float
    longitude: float
    altitude: float | None = None
    asset_type: str = "site"
    graph_node_id: str | None = None
    source: str = "manual"
    properties: dict[str, Any] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SpatialAssetStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.SPATIAL_ASSET_ROOT)

    def upsert(self, asset: SpatialAsset) -> SpatialAsset:
        asset.updated_at = datetime.now(UTC).isoformat()
        project_dir = self.root / asset.project_id
        os.makedirs(project_dir, exist_ok=True)
        (project_dir / f"{asset.asset_id}.json").write_text(
            json.dumps(asset.as_dict(), indent=2, sort_keys=True)
        )
        self._refresh_index(asset.project_id)
        return asset

    def list_assets(self, project_id: str) -> list[SpatialAsset]:
        project_dir = self.root / project_id
        if not project_dir.exists():
            return []
        assets = [
            SpatialAsset.model_validate(json.loads(path.read_text()))
            for path in sorted(project_dir.glob("asset_*.json"))
        ]
        return assets

    def get(self, project_id: str, asset_id: str) -> SpatialAsset | None:
        path = self.root / project_id / f"{asset_id}.json"
        if not path.exists():
            return None
        return SpatialAsset.model_validate(json.loads(path.read_text()))

    def delete(self, project_id: str, asset_id: str) -> bool:
        path = self.root / project_id / f"{asset_id}.json"
        if not path.exists():
            return False
        path.unlink()
        self._refresh_index(project_id)
        return True

    def _refresh_index(self, project_id: str) -> None:
        index = [asset.as_dict() for asset in self.list_assets(project_id)]
        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        (project_dir / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True))


def extract_coordinates(properties: dict[str, Any]) -> tuple[float, float, float | None] | None:
    lat_keys = ("latitude", "lat", "y")
    lon_keys = ("longitude", "lon", "lng", "x")
    alt_keys = ("altitude", "alt", "elevation", "z")

    lat = _first_numeric(properties, lat_keys)
    lon = _first_numeric(properties, lon_keys)
    if lat is None or lon is None:
        return None

    alt = _first_numeric(properties, alt_keys)
    return lat, lon, alt


def _first_numeric(properties: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in properties:
            try:
                return float(properties[key])
            except (TypeError, ValueError):
                continue
    return None
