# ProjectForge AI v14 — Status

Last updated: Sprint 18 complete on branch `cursor/sprint18-airgap-hardening-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 128 tests
python3 scripts/smoke_portfolio_intelligence.py
python3 scripts/build_airgap_bundle.py --version 14.0.0 --skip-wheels
python3 scripts/check_graph_schema_version.py
helm template projectforge ./deploy/helm/projectforge
cd frontend && npm run typecheck
```

## New in Sprint 18

- **Air-gap bundles** — `build_airgap_bundle.py` / `apply_airgap_bundle.py` with manifest checksums
- **Production hardening** — security headers, HSTS, restricted CORS when `PRODUCTION_HARDENING=true`
- **Deploy status API** — `/api/v1/deploy/status` with build info and hardening flags
- **Helm TLS defaults** — SSL redirect ingress annotations, OIDC + hardening enabled by default
- **CI smoke** — portfolio intelligence smoke test and source-only bundle build

## Backend modules

| Module | Status |
|--------|--------|
| Ingestion pipeline | PDF, EML, mbox, Office, OCR, nested attachments, manifest |
| Graph builder | Manifest projection, LLM enrich, mutations, rebuild + orphan cleanup |
| Neo4j adapter | Versioned bootstrap (`SCHEMA_VERSION=2`), in-memory fallback |
| Orchestrator | Specialist agents, per-step checkpoints, run history, resume |
| LangGraph runner | Optional sequential + conditional branching |
| Compliance | Profiles, redaction, audit, SOC 2 export |
| Auth / SSO | OIDC scaffolding, session tokens |
| Portfolio intelligence | Compliance/risk rollups, executive dashboard, portfolio orchestrator |
| Deploy ops | Air-gap bundles, production hardening middleware, deploy status |

## Resume development

```bash
git checkout cursor/sprint18-airgap-hardening-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
