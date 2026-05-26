"""GPG signature helpers for air-gapped update bundles."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def gpg_available() -> bool:
    return shutil.which("gpg") is not None


def sign_file(*, path: Path, key_id: str, output_path: Path | None = None) -> Path:
    if not gpg_available():
        raise RuntimeError("gpg is not installed")
    signature_path = output_path or Path(f"{path}.asc")
    subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--local-user",
            key_id,
            "--detach-sign",
            "--armor",
            "--output",
            str(signature_path),
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return signature_path


def verify_signature(
    *,
    archive: Path,
    signature_path: Path | None = None,
    public_key_path: Path | None = None,
) -> dict[str, Any]:
    if not gpg_available():
        raise RuntimeError("gpg is not installed")

    sig = signature_path or Path(f"{archive}.asc")
    if not sig.exists():
        raise ValueError(f"Signature file not found: {sig}")

    command = ["gpg", "--batch", "--verify", str(sig), str(archive)]
    if public_key_path:
        subprocess.run(
            ["gpg", "--batch", "--import", str(public_key_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "GPG verification failed"
        raise ValueError(detail)

    return {
        "verified": True,
        "archive": str(archive),
        "signature": str(sig),
        "public_key": str(public_key_path) if public_key_path else None,
        "gpg_output": result.stderr.strip() or result.stdout.strip(),
    }
