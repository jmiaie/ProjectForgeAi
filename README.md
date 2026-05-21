# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.**

Master Build Framework v14 + **Forge CLI** for spec-driven scaffolding.

## Highlights

- LangGraph orchestrator + specialist agents
- Postgres (SQLAlchemy + Alembic), encrypted connections, audit log
- OAuth 2.0 / PKCE (Google, GitHub, Microsoft, Slack)
- Living project graph (Neo4j-ready + React Flow export)
- Temporal-style automations — recurring reports, digests, compliance scans
- **PDF ingestion (Phase 1)** — tables, forms, OCR fallback, sliding-window chunking
- Forge CLI + REST API for JSON spec validate/plan

## Quick start

```bash
cp .env.example .env && docker-compose up -d
cd backend && pip install -r requirements.txt && python -m alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

<<<<<<< HEAD
=======
The intake wizard is mounted at `/` and `/settings/connections` and talks to the FastAPI backend at `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`).

## Key Endpoints

| Method | Path                                   | Purpose                                       |
| ------ | -------------------------------------- | --------------------------------------------- |
| GET    | `/health`                              | Liveness + version                            |
| POST   | `/api/v1/auth/register`                | Create user + auto-provisioned organization   |
| POST   | `/api/v1/auth/login`                   | Issue JWT access token                        |
| GET    | `/api/v1/auth/me`                      | Current user + organizations (auth required)  |
| POST   | `/api/v1/orgs/`                        | Create organization (caller becomes owner)    |
| GET    | `/api/v1/orgs/`                        | List the caller's organizations               |
| GET    | `/api/v1/orgs/{id}`                    | Fetch an organization (viewer+ required)      |
| GET    | `/api/v1/orgs/{id}/members`            | List members (viewer+ required)               |
| POST   | `/api/v1/orgs/{id}/members`            | Add a member by email (admin+ required)       |
| DELETE | `/api/v1/orgs/{id}/members/{user_id}`  | Remove a member (admin+ required)             |
| GET    | `/api/v1/intake/connectors`            | List recommended connectors per tier          |
| POST   | `/api/v1/intake/connections`           | Authenticate + persist a connector (encrypted) |
| GET    | `/api/v1/intake/connections`           | List persisted connections                    |
| GET    | `/api/v1/intake/oauth/providers`       | List OAuth providers + default scopes         |
| GET    | `/api/v1/intake/oauth/{provider}/authorize` | Begin OAuth flow (returns authorize URL) |
| GET    | `/api/v1/intake/oauth/{provider}/callback`  | OAuth redirect target — exchanges code   |
| POST   | `/api/v1/projects/`                    | Create project, ingest files, plan agents (anon or authed) |
| GET    | `/api/v1/projects/`                    | List projects                                 |
| GET    | `/api/v1/projects/{project_id}`        | Fetch single project                          |
| DELETE | `/api/v1/projects/{project_id}`        | Delete project (admin+ in project's org)      |
| POST   | `/api/v1/agents/orchestrate`           | Run orchestrator standalone                   |
| GET    | `/api/v1/agents/specialists`           | List specialist agents                        |
| GET    | `/api/v1/audit/`                       | Query audit log (filter by project / action)  |
| GET    | `/api/v1/projects/{id}/graph/`         | Full project graph (nodes + edges)            |
| GET    | `/api/v1/projects/{id}/graph/stats`    | Per-kind node + edge counts                   |
| GET    | `/api/v1/projects/{id}/graph/react-flow` | React Flow-shaped payload                   |
| GET    | `/api/v1/projects/{id}/graph/nodes/{node_id}` | Fetch a single node                    |
| GET    | `/api/v1/projects/{id}/graph/schema`   | Node + edge taxonomy                          |
| GET    | `/api/v1/automations/kinds`            | List automation kinds + default intervals     |
| POST   | `/api/v1/projects/{id}/automations/`   | Schedule a recurring automation               |
| GET    | `/api/v1/projects/{id}/automations/`   | List automations for a project                |
| GET    | `/api/v1/projects/{id}/automations/{automation_id}` | Fetch a single automation         |
| POST   | `/api/v1/projects/{id}/automations/{automation_id}/run-now` | Trigger one cycle now      |
| DELETE | `/api/v1/projects/{id}/automations/{automation_id}` | Cancel an automation              |

### Migrations

Alembic is configured against the same `DATABASE_URL` your app uses. From `backend/`:

>>>>>>> origin/cursor/sprint-7-auth-rbac-dc5d
```bash
npm ci && npm run build && npm test
npm run forge -- run --spec ./examples/specs/api-service.json --output ./api-out
```

## API endpoints (summary)

| Area | Examples |
| ---- | -------- |
| Health | `GET /health` |
| Intake | `GET /api/v1/intake/connectors`, `POST .../connections` |
| OAuth | `GET /api/v1/intake/oauth/{provider}/authorize` |
| Projects | `POST /api/v1/projects/`, `GET /api/v1/projects/{id}` |
| Graph | `GET /api/v1/projects/{id}/graph/react-flow` |
| Agents | `POST /api/v1/agents/orchestrate` |
| Automations | `POST /api/v1/projects/{id}/automations/`, `POST .../run-now` |
| Forge | `POST /api/v1/forge/validate`, `POST /api/v1/forge/plan` |
| Audit | `GET /api/v1/audit/` |

OpenAPI docs: http://localhost:8000/docs

## PDF ingestion (Sprint 6)

`app.ingestion.parsers.common.PDFParser`:

- Per-page text with width / height / rotation metadata
- Sliding-window chunking (`app.ingestion.chunking`)
- AcroForm fields → `section: form_fields` chunks
- Tables via pdfplumber → `section: table` chunks
- OCR fallback (pypdfium2 + pytesseract) for scanned pages

Optional dependencies degrade gracefully; warnings appear in parser output.

## Integrated sprints

| Sprint | Status |
| ------ | ------ |
| 1 LangGraph | Done |
| 2 Persistence | Done |
| 3 OAuth | Done |
| 4 Project graph | Done |
| 5 Automations | Done |
| 6 PDF hardening | Done |
| 7–11 | In progress |

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
