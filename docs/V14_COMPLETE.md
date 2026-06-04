# Master Build Framework v14 — Completion Checklist

ProjectForge AI v14 is **feature-complete** on branch `cursor/v14-complete-dc5d`. This document maps framework phases to shipped sprints.

## Phase 1 — Core platform

| Capability | Sprint | Status |
| ---------- | ------ | ------ |
| Monorepo scaffold (FastAPI + Next.js + Docker) | 0 | Done |
| LangGraph orchestrator + 5 specialists | 1 | Done |
| SQLAlchemy persistence + Fernet encryption | 2 | Done |
| OAuth 2.0 / PKCE (Google, Microsoft, GitHub, Slack) | 3 | Done |
| Project graph (Neo4j + in-memory adapter) | 4 | Done |
| Automations (Temporal stub + in-memory engine) | 5 | Done |
| PDF hardening (tables, OCR, forms) | 6 | Done |
| Multi-tenant auth + RBAC | 7 | Done |
| Locus BM25 + OMPA journal engines | 8 | Done |

## Phase 2 — Ingestion + UI

| Capability | Sprint | Status |
| ---------- | ------ | ------ |
| Helm / Docker prod / air-gapped deploy | 9 | Done |
| CAD (DXF) + BIM (IFC) ingestion | 10 | Done |
| Source-code repo archive ingestion | 11 | Done |
| Frontend dashboard (Graph, Gantt, Chat) | 12 | Done |
| Full-stack Docker + API proxy + CI | 13 | Done |
| Helm frontend ingress + API E2E | 14 | Done |
| CI-stable LLM stubs + Playwright smoke | 15 | Done |

## Phase 3 — Integration polish

| Capability | Sprint | Status |
| ---------- | ------ | ------ |
| RTK context optimization (orchestrator) | 16 | Done |
| Submodule scaffolding + setup script | 17 | Done |
| Webhook ingestion + system status API | 18 | Done |

## Verification

```bash
# Backend (115+ tests, no live LLM keys required)
cd backend && PYTHONPATH=. python3 -m pytest -q

# Frontend build + Playwright smoke
cd frontend && npm ci && npm run build && npm run test:e2e

# Full stack
cp .env.example .env && docker compose up -d --build
curl http://localhost:8000/api/v1/system/status
open http://localhost:3000/projects
```

## Merge to `main`

Follow [MERGE.md](./MERGE.md) for the stacked PR series, **or** merge this release branch directly:

```bash
git checkout main
git merge cursor/v14-complete-dc5d
```

Before production: rotate `ENCRYPTION_KEY`, `JWT_SECRET`, and database passwords per [deploy/README.md](../deploy/README.md).

## Post-v14 (optional future work)

- Wire upstream Locus/OMPA/RTK git submodules when repos are published
- Full-stack Playwright tests against Docker Compose in CI
- Portfolio / billing / observability tracks (separate enterprise branches)
