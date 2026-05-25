import subprocess
from typing import Any

from spatial.store import SpatialAsset, SpatialAssetStore


class RTKAdapter:
    """RTK spatial adapter for geo-tagged project assets."""

    def __init__(
        self,
        project_id: str,
        *,
        enabled: bool = True,
        store: SpatialAssetStore | None = None,
    ):
        self.project_id = project_id
        self.enabled = enabled
        self.rtk_path = "rtk"
        self.store = store or SpatialAssetStore()

    def status(self) -> dict[str, Any]:
        assets = self.store.list_assets(self.project_id)
        return {
            "backend": "rtk",
            "enabled": self.enabled,
            "project_id": self.project_id,
            "asset_count": len(assets),
            "rtk_cli_available": _rtk_cli_available(self.rtk_path),
        }

    def list_assets(self) -> list[SpatialAsset]:
        return self.store.list_assets(self.project_id)

    def register_asset(self, asset: SpatialAsset) -> SpatialAsset:
        asset.project_id = self.project_id
        return self.store.upsert(asset)

    async def execute_command(self, cmd: str, cwd: str | None = None) -> dict[str, Any]:
        if self.enabled:
            cmd = f"{self.rtk_path} {cmd}"
        result = subprocess.run(cmd, shell=True, capture_output=True, cwd=cwd, check=False)
        return {
            "output": result.stdout.decode(),
            "error": result.stderr.decode(),
            "returncode": result.returncode,
            "compressed": self.enabled,
        }


def _rtk_cli_available(rtk_path: str) -> bool:
    try:
        result = subprocess.run(
            [rtk_path, "--version"],
            capture_output=True,
            check=False,
            timeout=2,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
