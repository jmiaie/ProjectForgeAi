#!/usr/bin/env python3
"""Smoke test portfolio intelligence endpoints (CI-friendly, no live server)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "app"))

from fastapi.testclient import TestClient

import main


def run_smoke() -> None:
    client = TestClient(main.app)

    dashboard = client.get("/api/v1/portfolio/intelligence/dashboard")
    if dashboard.status_code != 200:
        raise SystemExit(f"dashboard smoke failed: {dashboard.status_code}")
    widgets = dashboard.json().get("widgets", {})
    for key in ("portfolio_health", "compliance_posture", "risk_summary"):
        if key not in widgets:
            raise SystemExit(f"dashboard missing widget: {key}")

    compliance = client.get("/api/v1/portfolio/compliance/rollup")
    if compliance.status_code != 200:
        raise SystemExit(f"compliance rollup smoke failed: {compliance.status_code}")
    if "by_category" not in compliance.json():
        raise SystemExit("compliance rollup missing by_category")

    risk = client.get("/api/v1/portfolio/risk/rollup")
    if risk.status_code != 200:
        raise SystemExit(f"risk rollup smoke failed: {risk.status_code}")
    if "by_severity" not in risk.json():
        raise SystemExit("risk rollup missing by_severity")

    summary = client.get("/api/v1/portfolio/summary")
    if summary.status_code != 200:
        raise SystemExit(f"portfolio summary smoke failed: {summary.status_code}")

    print("portfolio intelligence smoke passed")


if __name__ == "__main__":
    run_smoke()
