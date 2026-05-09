# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.** Upload all project documents once → instant living project graph → auto-generates every template, contract, schedule, automation, communication loop, and compliance control.

This repository implements the **Master Build Framework v14**.

---

## Highlights

- **Industry-agnostic** PM framework that adapts from solopreneur gigs to enterprise programs.
- **100% accuracy grounding** via Locus (vectorless RAG) + OMPA (persistent memory) + Neo4j project graph.
- **LLM-flexible** by design: low-cost defaults, flagship upsell, and full Bring-Your-Own-Key via LiteLLM.
- **Intake / Connections Wizard** with OAuth 2.0 / PKCE, API keys, webhooks, and MCP tool discovery.
- **Compliance-first**: HIPAA, SOC 2, GDPR, legal modes — with self-improvement gated by category.
- **Parallel-build ready**: scaffolded so Cursor, Claude, Grok, Lovable and Manus can ship in parallel.

## Repository Layout

```
projectforge-ai/
├── backend/
│   ├── app/
│   │   ├── core/              # config, llm_router, integrations_manager
│   │   ├── compliance/        # enforcer, profiles
│   │   ├── integrations/      # registry, intake_form, connectors (oauth/api_key/mcp)
│   │   ├── storage/           # locus, ompa, rtk adapters
│   │   ├── ingestion/         # pipeline + parsers/common (pdf, image, email)
│   │   ├── agents/            # orchestrator (LangGraph-ready)
│   │   ├── api/               # FastAPI routers (projects, ...)
│   │   └── main.py            # FastAPI entry point
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                   # Next.js 15 app router
│   ├── components/            # IntakeWizard.tsx + UI
│   └── package.json
├── submodules/                # locus / ompa / rtk (added as git submodules)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

```bash
# 1. Configure env
cp .env.example .env

# 2. Bring up Postgres / Neo4j / Redis / backend
docker-compose up -d

# 3. Open the API
open http://localhost:8000/health
open http://localhost:8000/docs
```

### Backend (local, without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The intake wizard is mounted at `/` and `/settings/connections` and talks to the FastAPI backend at `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`).

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

```bash
python -m alembic upgrade head     # apply schema
python -m alembic downgrade base   # roll back
python -m alembic revision --autogenerate -m "describe change"
```

For local dev / tests the app will also auto-create tables on startup when `AUTO_CREATE_SCHEMA=true`. Production should rely on Alembic only.

## Parallel Development

| Tool        | Focus                                                         |
| ----------- | ------------------------------------------------------------- |
| Cursor      | Final integration, local running, git workflow                |
| Claude Opus | Deep agent logic & full LangGraph orchestrator                |
| Grok        | Master framework coordination                                 |
| Lovable     | Rapid full-stack UI + frontend backend bindings               |
| Manus       | Autonomous testing (OAuth flows, MCP connectors, ingestion)   |

## Phase 1 Roadmap

1. PDF parser hardening (tables, scans, structured forms).
2. Complete LangGraph orchestrator with specialist agents.
3. Locus + OMPA submodule wiring (replace in-memory fallbacks).
4. Temporal-driven recurring comms / reports.
5. Hybrid + on-prem deployment manifests.

## License

Proprietary — ProjectForge AI. All rights reserved.
