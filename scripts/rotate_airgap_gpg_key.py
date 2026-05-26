#!/usr/bin/env python3
"""Rotate GPG signing keys for ProjectForge air-gap bundles."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY_DIR = ROOT / "deploy" / "airgap" / "keys"


def gpg_available() -> bool:
    return shutil.which("gpg") is not None


def export_public_key(key_id: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["gpg", "--batch", "--armor", "--export", key_id],
        check=True,
        stdout=open(output_path, "w"),
    )
    return output_path


def import_public_key(public_key_path: Path) -> None:
    subprocess.run(["gpg", "--batch", "--import", str(public_key_path)], check=True)


def generate_rotation_manifest(
    *,
    old_key_id: str | None,
    new_key_id: str,
    public_key_path: Path,
    notes: str = "",
) -> dict:
    return {
        "rotated_at": datetime.now(UTC).isoformat(),
        "old_key_id": old_key_id,
        "new_key_id": new_key_id,
        "public_key_path": str(public_key_path),
        "notes": notes,
        "next_steps": [
            "Distribute the new public key to air-gapped environments",
            "Update AIRGAP_GPG_PUBLIC_KEY_PATH in production env",
            "Re-sign pending bundles with the new private key",
            "Keep the old public key for verifying historical bundles until retired",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate ProjectForge air-gap GPG signing key")
    parser.add_argument("--new-key-id", required=True, help="New GPG key id or email")
    parser.add_argument("--old-key-id", help="Previous key id for manifest tracking")
    parser.add_argument("--output-dir", default=str(DEFAULT_KEY_DIR))
    parser.add_argument("--import-only", help="Import an existing public key file")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    if not gpg_available():
        raise SystemExit("gpg is not installed")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.import_only:
        import_public_key(Path(args.import_only))
        public_key_path = output_dir / "release.imported.pub.asc"
        shutil.copy2(args.import_only, public_key_path)
    else:
        public_key_path = output_dir / "release.pub.asc"
        export_public_key(args.new_key_id, public_key_path)

    manifest = generate_rotation_manifest(
        old_key_id=args.old_key_id,
        new_key_id=args.new_key_id,
        public_key_path=public_key_path,
        notes=args.notes,
    )
    manifest_path = output_dir / "rotation.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({"manifest": str(manifest_path), "public_key": str(public_key_path)}, indent=2))


if __name__ == "__main__":
    main()
