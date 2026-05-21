# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.** Upload all project documents once → instant living project graph → auto-generates every template, contract, schedule, automation, communication loop, and compliance control.

This repository implements the **Master Build Framework v14**, plus a **Forge CLI** for spec-driven repository scaffolding.

---

## Highlights

- **Industry-agnostic** PM framework from solopreneur gigs to enterprise programs.
- **LangGraph orchestrator** with specialist agents (compliance, schedule, contracts, risk, comms).
- **Postgres persistence** — projects, encrypted connections, audit log (SQLAlchemy + Alembic).
- **OAuth 2.0 / PKCE** for Google, GitHub, Microsoft, Slack.
- **Living project graph** — Neo4j-ready adapter + React Flow export API.
- **LLM-flexible** via LiteLLM (BYOK supported).
- **Forge CLI** — JSON spec → versioned recipes (`minimal`, `express-api`).

## Repository layout

```
├── backend/     # FastAPI, agents, db, oauth, graph
├── frontend/    # Next.js IntakeWizard
├── src/         # Forge CLI
├── templates/   # Forge recipes
└── docs/        # ADRs
```

## Quick start — platform

```bash
cp .env.example .env
docker-compose up -d
open http://localhost:8000/docs
```

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

## Quick start — Forge CLI

```bash
npm ci && npm run build && npm test
npm run forge -- run --spec ./examples/specs/api-service.json --output ./api-out
```

## API endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/health` | Liveness |
| GET | `/api/v1/intake/connectors` | List connectors |
| POST | `/api/v1/intake/connections` | Persist connection |
| GET | `/api/v1/intake/oauth/providers` | OAuth providers |
| GET | `/api/v1/intake/oauth/{provider}/authorize` | Start OAuth |
| GET | `/api/v1/intake/oauth/{provider}/callback` | OAuth callback |
| POST | `/api/v1/projects/` | Create project |
| GET | `/api/v1/projects/` | List projects |
| GET | `/api/v1/projects/{project_id}` | Get project |
| GET | `/api/v1/projects/{project_id}/graph` | Project graph (React Flow JSON) |
| POST | `/api/v1/projects/{project_id}/graph/rebuild` | Rebuild graph from ingested docs |
| POST | `/api/v1/agents/orchestrate` | Run orchestrator |
| GET | `/api/v1/agents/specialists` | List specialists |
| GET | `/api/v1/audit/` | Audit log |

## Phase roadmap

| Phase | Status |
| ----- | ------ |
| v14 + Forge v0.2 | Done |
| Sprint 1 — LangGraph | Done |
| Sprint 2 — Persistence | Done |
| Sprint 3 — OAuth | Done |
| Sprint 4 — Project graph | Done |
| Sprint 5–11 | Open branches |

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
