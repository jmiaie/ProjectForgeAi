#!/usr/bin/env python3
"""Verify graph schema version is documented and consistent."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "app"))

from graph.bootstrap import SCHEMA_VERSION  # noqa: E402


def main() -> int:
    architecture = REPO_ROOT / "docs" / "ARCHITECTURE.md"
    text = architecture.read_text()
    match = re.search(r"SCHEMA_VERSION=(\d+)", text)
    if not match:
        print("docs/ARCHITECTURE.md missing SCHEMA_VERSION reference")
        return 1
    documented = int(match.group(1))
    if documented != SCHEMA_VERSION:
        print(f"Schema version mismatch: code={SCHEMA_VERSION} docs={documented}")
        return 1
    print(f"Graph schema version OK: {SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
