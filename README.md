# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.** Upload all project documents once → instant living project graph → auto-generates every template, contract, schedule, automation, communication loop, and compliance control.

This repository implements the **Master Build Framework v14**, plus a **Forge CLI** for spec-driven repository scaffolding.

---

## Highlights

- **Industry-agnostic** PM framework that adapts from solopreneur gigs to enterprise programs.
- **LangGraph-ready orchestrator** with specialist agents (compliance, schedule, contracts, risk, comms).
- **Postgres persistence** — projects, encrypted connections, audit log (SQLAlchemy + Alembic).
- **OAuth 2.0 / PKCE** — real authorization flows for Google, GitHub, Microsoft, Slack.
- **100% accuracy grounding** via Locus (vectorless RAG) + OMPA (persistent memory) + Neo4j project graph.
- **LLM-flexible** by design: low-cost defaults, flagship upsell, and full Bring-Your-Own-Key via LiteLLM.
- **Intake / Connections Wizard** with API keys, webhooks, and MCP tool discovery.
- **Compliance-first**: HIPAA, SOC 2, GDPR, legal modes.
- **Forge CLI** — versioned recipes produce reproducible project trees locally.

## Repository layout

```
├── backend/           # FastAPI — agents, db, oauth, ingestion
├── frontend/          # Next.js 15 — IntakeWizard, settings
├── src/               # Forge CLI (TypeScript)
├── templates/         # Forge recipes
├── docs/              # ADRs, architecture
└── docker-compose.yml
```

## Quick start — platform

```bash
cp .env.example .env
docker-compose up -d
open http://localhost:8000/health
open http://localhost:8000/docs
```

### Backend (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database migrations

From `backend/`:

```bash
python -m alembic upgrade head
python -m alembic downgrade base
```

Set `AUTO_CREATE_SCHEMA=true` for local dev only; production uses Alembic.

## Quick start — Forge CLI

```bash
npm ci && npm run build && npm test
npm run forge -- list
npm run forge -- run --spec ./examples/specs/api-service.json --output ./api-out
```

## API endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/health` | Liveness + version |
| GET | `/api/v1/intake/connectors` | List connectors per tier |
| POST | `/api/v1/intake/connections` | Persist connector (encrypted) |
| GET | `/api/v1/intake/connections` | List connections |
| GET | `/api/v1/intake/oauth/providers` | OAuth providers + scopes |
| GET | `/api/v1/intake/oauth/{provider}/authorize` | Start OAuth (returns authorize URL) |
| GET | `/api/v1/intake/oauth/{provider}/callback` | OAuth redirect callback |
| POST | `/api/v1/projects/` | Create project + ingest |
| GET | `/api/v1/projects/` | List projects |
| GET | `/api/v1/projects/{project_id}` | Get project |
| POST | `/api/v1/agents/orchestrate` | Run orchestrator |
| GET | `/api/v1/agents/specialists` | List specialists |
| GET | `/api/v1/audit/` | Query audit log |

## Phase roadmap

| Phase | Status | Focus |
| ----- | ------ | ----- |
| v14 + Forge v0.2 | Done | Scaffold + spec planner |
| Sprint 1 | Done | LangGraph orchestrator |
| Sprint 2 | Done | Postgres + Alembic |
| Sprint 3 | Done | OAuth 2.0 / PKCE |
| Sprint 4+ | Pending | Project graph, Temporal, … |

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
