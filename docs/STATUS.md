# ProjectForge AI v14 — Status

Last updated: Sprint 16 complete on branch `cursor/sprint16-identity-deploy-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 118 tests
python3 scripts/check_graph_schema_version.py
helm template projectforge ./deploy/helm/projectforge
cd frontend && npm run typecheck
```

## New in Sprint 16

- **SSO/OIDC scaffolding** — session store, mock login, OIDC callback flow, Bearer token actor resolution
- **Helm chart** — `deploy/helm/projectforge/` for Kubernetes on-prem installs
- **SOC 2 export** — control mapping starter with audit/RBAC evidence aggregation
- **Login page** — `/login` with mock SSO for development
- **Compliance export UI** — Export SOC 2 button in CompliancePanel

## Backend modules

| Module | Status |
|--------|--------|
| Ingestion pipeline | PDF, EML, mbox, Office, OCR, nested attachments, manifest |
| Graph builder | Manifest projection, LLM enrich, mutations, rebuild + orphan cleanup |
| Neo4j adapter | Versioned bootstrap (`SCHEMA_VERSION=2`), in-memory fallback |
| Orchestrator | Specialist agents, per-step checkpoints, run history, resume |
| LangGraph runner | Optional sequential + conditional branching (`USE_LANGGRAPH_ORCHESTRATOR`) |
| Compliance | Profiles, redaction, memory/external-write gates, audit, SOC 2 export |
| Auth / SSO | OIDC provider scaffolding, session tokens, group→role mapping |
| Integrations | OAuth PKCE, encrypted storage, MCP HTTP discovery |
| Automations | Local store, scheduling, Temporal worker, dead letters |

## Frontend panels

Upload, graph build/enrich/edit, timeline/Gantt, workbench, orchestrator (artifacts + history), compliance (SOC 2 export), connections (live health), automations (approve/history/temporal), access (SSO status), map.

## Resume development

```bash
git checkout cursor/sprint16-identity-deploy-ebb0
git pull origin cursor/sprint16-identity-deploy-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for Phase 5 priorities.
