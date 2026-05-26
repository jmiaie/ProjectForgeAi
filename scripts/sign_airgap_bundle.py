#!/usr/bin/env python3
"""Sign an air-gapped ProjectForge bundle with GPG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "app"))

from core.bundle_gpg import gpg_available, sign_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Sign ProjectForge air-gap bundle")
    parser.add_argument("archive", help="Path to projectforge-airgap-*.tar.gz")
    parser.add_argument("--key-id", required=True, help="GPG key id or email")
    parser.add_argument("--output", help="Optional signature output path")
    args = parser.parse_args()

    if not gpg_available():
        raise SystemExit("gpg is not installed")

    archive = Path(args.archive)
    signature = sign_file(
        path=archive,
        key_id=args.key_id,
        output_path=Path(args.output) if args.output else None,
    )
    print(json.dumps({"archive": str(archive), "signature": str(signature)}, indent=2))


if __name__ == "__main__":
    main()
