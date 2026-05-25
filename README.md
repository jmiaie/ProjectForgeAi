# ProjectForge AI v14

**PM framework in a box** — upload project documents, build a living graph, run specialist agents, enforce compliance, and automate workflows.

## Quick start

```bash
cp .env.example .env
docker compose up backend frontend automation-worker temporal neo4j postgres
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| Health | http://localhost:8000/health |
| Neo4j Browser | http://localhost:7474 |

Native development:

```bash
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000

cd frontend && npm install && npm run dev
```

Tests: `PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests` (100 tests)

## What ships today

- **Ingestion** — PDF, email, mbox, Office (DOCX/XLSX/PPTX), image OCR, nested attachments
- **Graph** — Neo4j with in-memory fallback, bootstrap/migrations, enrich, node/edge CRUD, orphan cleanup
- **Orchestrator** — five specialist agents, checkpoints, run history, resume; optional LangGraph with conditional branching; orchestrator audit trail
- **Compliance** — standard/HIPAA/legal/SOC2/GDPR profiles, redaction, audit trail
- **Integrations** — OAuth PKCE (production credential gate), encrypted API keys, MCP HTTP/SSE/stdio discovery, webhook connector, connection health UI
- **Enterprise** — RBAC scaffolding, upgrade manager, on-prem Compose overlay, self-improvement gate
- **Portfolio** — multi-project registry, cross-project summaries, project switcher UI
- **Ingestion expansion** — IFC/DWG CAD stubs, codebase archives, PostgreSQL schema snapshots
- **LLM billing** — flagship upsell routing, BYO keys, per-project usage metering
- **Automations** — scheduling, Temporal worker, approvals, dead letters, optional Schedule sync
- **Frontend** — editable React Flow graph, timeline/Gantt, workbench, orchestrator artifacts, automation controls

## Repository layout

```text
backend/app/          FastAPI services (ingestion, graph, agents, compliance, integrations, automations)
frontend/             Next.js 15 dashboard
docs/                 Status, roadmap, API reference, architecture
docker-compose.yml    Full stack (backend, frontend, worker, temporal, neo4j, postgres)
PROJECTFORGE_V14.md   Agent handoff brief (vision + conventions)
```

## Key environment flags

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_LANGGRAPH_ORCHESTRATOR` | `false` | LangGraph StateGraph execution |
| `PROJECT_TIER` | `starter` | Feature tier (`starter`, `pro`, `enterprise`) |
| `PROJECT_TIER` | `starter` | Feature tier (`starter`, `pro`, `enterprise`) |
| `OAUTH_MOCK_TOKEN_EXCHANGE` | `true` | Mock OAuth tokens in dev |
| `TEMPORAL_SYNC_SCHEDULES` | `false` | Register Temporal Schedule API jobs |
| `NEO4J_BOOTSTRAP_ON_CONNECT` | `true` | Apply graph schema migrations on connect |
| `IMAGE_OCR_ENABLED` | `true` | Tesseract OCR for images |

See `.env.example` for Locus/OMPA paths, OAuth client IDs, and Temporal settings.

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/STATUS.md](docs/STATUS.md) | Current implementation snapshot and verification |
| [docs/NEXT_SPRINTS.md](docs/NEXT_SPRINTS.md) | Phase roadmap and sprint backlog |
| [docs/API.md](docs/API.md) | REST endpoint reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [PROJECTFORGE_V14.md](PROJECTFORGE_V14.md) | Full agent handoff for parallel development |
| [frontend/README.md](frontend/README.md) | Dashboard development notes |

## Branch chain

```text
main
 └── cursor/projectforge-v14-framework-ebb0
      └── cursor/graph-editing-scheduling-ebb0
           └── cursor/neo4j-edges-attachments-ebb0
                └── cursor/sprint345-hardening-ebb0
                     └── cursor/docs-phase3-ebb0
                          └── cursor/sprint9-10-integrations-ci-ebb0
                               └── cursor/sprint11-enterprise-ebb0
                                    └── cursor/sprint12-portfolio-ebb0
                                         └── cursor/sprint13-ingestion-ebb0
                                              └── cursor/sprint14-llm-billing-ebb0   ← active
```
