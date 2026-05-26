#!/usr/bin/env python3
"""Apply an offline/air-gapped ProjectForge update bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_bundle(archive: Path, work_dir: Path) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(work_dir, filter="data")
    bundle_dirs = [path for path in work_dir.iterdir() if path.is_dir()]
    if not bundle_dirs:
        raise ValueError("Archive did not contain a bundle directory")
    return bundle_dirs[0]


def _verify_manifest(bundle_dir: Path) -> dict:
    manifest_path = bundle_dir / "MANIFEST.json"
    if not manifest_path.exists():
        raise ValueError("MANIFEST.json missing from bundle")
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest.get("files", []):
        rel = entry["path"]
        expected = entry["sha256"]
        source_path = bundle_dir / "source" / rel
        if not source_path.exists():
            raise ValueError(f"Missing file in bundle: {rel}")
        actual = _sha256(source_path)
        if actual != expected:
            raise ValueError(f"Checksum mismatch for {rel}")
    return manifest


def apply_bundle(
    *,
    archive: Path,
    target_dir: Path,
    install_wheels: bool,
    require_signature: bool = False,
    public_key_path: Path | None = None,
    signature_path: Path | None = None,
) -> dict:
    if require_signature or public_key_path:
        import sys

        sys.path.insert(0, str(ROOT / "backend" / "app"))
        from core.bundle_gpg import verify_signature

        verify_signature(
            archive=archive,
            signature_path=signature_path,
            public_key_path=public_key_path,
        )

    work_dir = target_dir / ".airgap-work"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    bundle_dir = _extract_bundle(archive, work_dir)
    manifest = _verify_manifest(bundle_dir)

    source_dir = bundle_dir / "source"
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source_dir)
        destination = target_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    build_info_src = source_dir / "BUILD_INFO.json"
    if build_info_src.exists():
        shutil.copy2(build_info_src, target_dir / "BUILD_INFO.json")

    wheels_dir = bundle_dir / "wheels"
    if install_wheels and wheels_dir.exists() and any(wheels_dir.iterdir()):
        subprocess.run(
            [
                "python3",
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(wheels_dir),
                "-r",
                str(target_dir / "requirements.txt"),
            ],
            check=True,
        )

    deploy_notes = {
        "bundle_id": manifest.get("bundle_id"),
        "version": manifest.get("version"),
        "git_sha": manifest.get("git_sha"),
        "target_dir": str(target_dir),
        "signature_verified": bool(require_signature or public_key_path),
        "next_steps": [
            "Review .env / deploy/onprem/.env.prod.example before restart",
            "Docker: docker compose -f docker-compose.yml -f deploy/onprem/docker-compose.prod.yml up -d --build",
            "Helm: helm upgrade projectforge ./deploy/helm/projectforge -f my-values.yaml",
        ],
    }
    (target_dir / "AIRGAP_APPLY.json").write_text(json.dumps(deploy_notes, indent=2, sort_keys=True))
    shutil.rmtree(work_dir)
    return deploy_notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply ProjectForge air-gapped update bundle")
    parser.add_argument("archive", help="Path to projectforge-airgap-*.tar.gz")
    parser.add_argument("--target-dir", default=str(ROOT))
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--require-signature", action="store_true")
    parser.add_argument("--public-key", help="Path to GPG public key for bundle verification")
    parser.add_argument("--signature", help="Path to detached .asc signature")
    args = parser.parse_args()

    result = apply_bundle(
        archive=Path(args.archive),
        target_dir=Path(args.target_dir),
        install_wheels=not args.skip_pip,
        require_signature=args.require_signature,
        public_key_path=Path(args.public_key) if args.public_key else None,
        signature_path=Path(args.signature) if args.signature else None,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
