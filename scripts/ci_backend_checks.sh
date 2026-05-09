#!/usr/bin/env bash
set -euo pipefail

echo "[ci] compile backend sources"
python3 -m compileall backend/app

echo "[ci] run unittest backend suite"
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -p "test_*.py"

echo "[ci] run autonomous end-to-end harness"
PYTHONPATH=backend python3 scripts/manus_autonomous_test.py

echo "[ci] all backend checks passed"
