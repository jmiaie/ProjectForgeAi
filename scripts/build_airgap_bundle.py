#!/usr/bin/env python3
"""Build an offline/air-gapped update bundle for ProjectForge AI."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "airgap"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".rbac",
    ".projects",
    ".ingestion",
    ".orchestrator",
    ".audit",
    ".compliance",
    ".connections",
    ".auth-sessions",
    ".spatial",
    ".llm-keys",
    ".llm-usage",
    ".automations",
}

EXCLUDE_FILES = {".env", "BUILD_INFO.json"}


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _should_copy(rel: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    if rel.name in EXCLUDE_FILES:
        return False
    return True


def _copy_source(staging: Path) -> list[dict[str, str]]:
    source_root = staging / "source"
    files: list[dict[str, str]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if not _should_copy(rel):
            continue
        target = source_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        files.append({"path": str(rel).replace("\\", "/"), "sha256": _sha256(target)})
    return files


def _download_wheels(staging: Path) -> None:
    wheels_dir = staging / "wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)
    requirements = ROOT / "requirements.txt"
    subprocess.run(
        [
            "python3",
            "-m",
            "pip",
            "download",
            "-r",
            str(requirements),
            "-d",
            str(wheels_dir),
        ],
        cwd=ROOT,
        check=True,
    )


def _copy_deploy_assets(staging: Path) -> None:
    shutil.copytree(ROOT / "deploy" / "helm" / "projectforge", staging / "helm", dirs_exist_ok=True)
    shutil.copytree(ROOT / "deploy" / "onprem", staging / "onprem", dirs_exist_ok=True)
    shutil.copy2(ROOT / "docker-compose.yml", staging / "docker-compose.yml")
    shutil.copy2(ROOT / "requirements.txt", staging / "requirements.txt")
    shutil.copy2(ROOT / "scripts" / "apply_airgap_bundle.py", staging / "apply_airgap_bundle.py")


def build_bundle(*, output_dir: Path, version: str, skip_wheels: bool) -> Path:
    git_sha = _git_sha()
    bundle_id = f"projectforge-airgap-{version}-{git_sha}"
    staging = output_dir / bundle_id
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    files = _copy_source(staging)
    _copy_deploy_assets(staging)
    if not skip_wheels:
        _download_wheels(staging)

    manifest = {
        "bundle_id": bundle_id,
        "version": version,
        "git_sha": git_sha,
        "created_at": datetime.now(UTC).isoformat(),
        "file_count": len(files),
        "files": files,
        "includes_wheels": not skip_wheels,
    }
    (staging / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    build_info = {
        "bundle_id": bundle_id,
        "version": version,
        "git_sha": git_sha,
        "created_at": manifest["created_at"],
    }
    (staging / "source" / "BUILD_INFO.json").write_text(json.dumps(build_info, indent=2, sort_keys=True))

    archive_path = output_dir / f"{bundle_id}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(staging, arcname=bundle_id)

    shutil.rmtree(staging)
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ProjectForge air-gapped update bundle")
    parser.add_argument("--version", default="14.0.0")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--skip-wheels", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = build_bundle(output_dir=output_dir, version=args.version, skip_wheels=args.skip_wheels)
    print(json.dumps({"archive": str(archive), "size_bytes": archive.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
