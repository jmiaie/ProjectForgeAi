# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.** Upload all project documents once → instant living project graph → auto-generates every template, contract, schedule, automation, communication loop, and compliance control.

This repository implements the **Master Build Framework v14**, plus a **Forge CLI** for spec-driven repository scaffolding.

---

## Highlights

- **Industry-agnostic** PM framework that adapts from solopreneur gigs to enterprise programs.
- **LangGraph-ready orchestrator** with specialist agents (compliance, schedule, contracts, risk, comms).
- **Postgres persistence** — projects, encrypted connections, audit log (SQLAlchemy + Alembic).
- **100% accuracy grounding** via Locus (vectorless RAG) + OMPA (persistent memory) + Neo4j project graph.
- **LLM-flexible** by design: low-cost defaults, flagship upsell, and full Bring-Your-Own-Key via LiteLLM.
- **Intake / Connections Wizard** with OAuth 2.0 / PKCE, API keys, webhooks, and MCP tool discovery.
- **Compliance-first**: HIPAA, SOC 2, GDPR, legal modes — with self-improvement gated by category.
- **Forge CLI** — versioned recipes produce reproducible project trees locally (see below).
- **Parallel-build ready**: scaffolded so Cursor, Claude, Grok, Lovable and Manus can ship in parallel.

## Repository layout

```
├── backend/           # FastAPI — agents, db, ingestion, integrations
├── frontend/          # Next.js 15 — IntakeWizard, settings
├── src/               # Forge CLI + engine (TypeScript)
├── templates/         # Versioned forge recipes
├── docs/              # Vision, architecture, ADRs
├── docker-compose.yml
└── .github/workflows  # CI (backend + forge)
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
python -m alembic upgrade head   # or set AUTO_CREATE_SCHEMA=true for dev
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database migrations

<<<<<<< HEAD
From `backend/`:
=======
## Key Endpoints

| Method | Path                                   | Purpose                                       |
| ------ | -------------------------------------- | --------------------------------------------- |
| GET    | `/health`                              | Liveness + version                            |
| GET    | `/api/v1/intake/connectors`            | List recommended connectors per tier          |
| POST   | `/api/v1/intake/connections`           | Authenticate + persist a connector (encrypted) |
| GET    | `/api/v1/intake/connections`           | List persisted connections                    |
| GET    | `/api/v1/intake/oauth/providers`       | List OAuth providers + default scopes         |
| GET    | `/api/v1/intake/oauth/{provider}/authorize` | Begin OAuth flow (returns authorize URL) |
| GET    | `/api/v1/intake/oauth/{provider}/callback`  | OAuth redirect target — exchanges code   |
| POST   | `/api/v1/projects/`                    | Create project, ingest files, plan agents     |
| GET    | `/api/v1/projects/`                    | List projects                                 |
| GET    | `/api/v1/projects/{project_id}`        | Fetch single project                          |
| POST   | `/api/v1/agents/orchestrate`           | Run orchestrator standalone                   |
| GET    | `/api/v1/agents/specialists`           | List specialist agents                        |
| GET    | `/api/v1/audit/`                       | Query audit log (filter by project / action)  |

### Migrations

Alembic is configured against the same `DATABASE_URL` your app uses. From `backend/`:
>>>>>>> origin/cursor/sprint-3-oauth-flow-dc5d

```bash
python -m alembic upgrade head
python -m alembic downgrade base
python -m alembic revision --autogenerate -m "describe change"
```

For local dev/tests, tables auto-create on startup when `AUTO_CREATE_SCHEMA=true`. Production should use Alembic only.

## Quick start — Forge CLI

**Requirements:** Node.js 20+

```bash
npm ci
npm run build
npm test
npm run forge -- list
npm run forge -- run --recipe minimal --output ./my-new-project --name my-app
npm run forge -- validate --spec ./examples/specs/api-service.json
npm run forge -- run --spec ./examples/specs/api-service.json --output ./api-out
```

| Doc | Description |
|-----|-------------|
| [docs/vision.md](docs/vision.md) | Forge vision & scope |
| [docs/architecture.md](docs/architecture.md) | Forge components |
| [docs/adr/001-execution-model.md](docs/adr/001-execution-model.md) | Safety defaults |
| [docs/adr/002-spec-planner.md](docs/adr/002-spec-planner.md) | JSON spec planner |

## API endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/health` | Liveness + version |
| GET | `/api/v1/intake/connectors` | List connectors per tier |
| POST | `/api/v1/intake/connections` | Authenticate + persist connector (encrypted) |
| GET | `/api/v1/intake/connections` | List persisted connections |
| POST | `/api/v1/projects/` | Create project, ingest files, plan agents |
| GET | `/api/v1/projects/` | List projects |
| GET | `/api/v1/projects/{project_id}` | Fetch single project |
| POST | `/api/v1/agents/orchestrate` | Run orchestrator standalone |
| GET | `/api/v1/agents/specialists` | List specialist agents |
| GET | `/api/v1/audit/` | Query audit log |

## Phase roadmap

| Phase | Status | Focus |
| ----- | ------ | ----- |
| v14 scaffold | Done | Backend, frontend, docker-compose |
| Forge v0.2 | Done | JSON spec, `express-api`, `validate` |
| Sprint 1 | Done | LangGraph orchestrator + specialists |
| Sprint 2 | Done | Postgres + Alembic + audit |
| Sprint 3–11 | Branches | OAuth, project graph, Temporal, … |

## License

Platform components: proprietary — ProjectForge AI. Forge CLI tooling: MIT — see [LICENSE](LICENSE).
