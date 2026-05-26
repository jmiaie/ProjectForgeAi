import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BUILD_INFO_PATHS = (
    Path("BUILD_INFO.json"),
    Path("/workspace/BUILD_INFO.json"),
    Path(__file__).resolve().parents[3] / "BUILD_INFO.json",
)


@lru_cache(maxsize=1)
def load_build_info() -> dict[str, Any]:
    for path in BUILD_INFO_PATHS:
        if path.exists():
            try:
                payload = json.loads(path.read_text())
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                continue
    return {}


def build_info_status() -> dict[str, Any]:
    info = load_build_info()
    if not info:
        return {"present": False}
    return {
        "present": True,
        "version": info.get("version"),
        "git_sha": info.get("git_sha"),
        "bundle_id": info.get("bundle_id"),
        "created_at": info.get("created_at"),
    }
