# ProjectForge AI v14 — Status

Last updated: Sprint 19 complete on branch `cursor/sprint19-saas-observability-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 133 tests
python3 scripts/smoke_portfolio_intelligence.py
python3 scripts/build_airgap_bundle.py --version 14.0.0 --skip-wheels
cd frontend && npm run typecheck
```

## New in Sprint 19

- **GPG bundle signing** — sign/verify air-gap bundles with detached `.asc` signatures
- **Multi-tenant isolation** — tenant registry, header-scoped project stores when `TENANT_ISOLATION_ENABLED=true`
- **Observability** — request metrics, trace buffer, `X-Request-ID`, `/api/v1/observability/*`
- **ObservabilityPanel** — dashboard widget for request/error/latency stats

## Backend modules

| Module | Status |
|--------|--------|
| Tenancy | Registry, context header, scoped data roots |
| Observability | Metrics collector, trace buffer, middleware |
| Deploy ops | Air-gap bundles with optional GPG verification |
| Portfolio intelligence | Rollups, executive dashboard, portfolio orchestrator |
| Auth / SSO | OIDC scaffolding, session tokens |
| Compliance | Profiles, audit, SOC 2 export |

## Resume development

```bash
git checkout cursor/sprint19-saas-observability-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
