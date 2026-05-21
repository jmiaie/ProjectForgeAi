# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.**

Master Build Framework v14 + **Forge CLI** for spec-driven scaffolding.

## Highlights

- LangGraph orchestrator + specialist agents
- Postgres + Alembic, encrypted connections, audit log
- OAuth 2.0 / PKCE for connectors
- **Multi-tenant auth + RBAC** — JWT, organizations, roles (owner/admin/member/viewer)
- Living project graph (Neo4j-ready + React Flow export)
- Temporal-style automations
- PDF ingestion — tables, forms, OCR fallback, chunking
- Forge CLI + REST API

## Quick start

```bash
cp .env.example .env && docker-compose up -d
cd backend && pip install -r requirements.txt && python -m alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

```bash
npm ci && npm run build && npm test
```

### Auth (Sprint 7)

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"secret","name":"You"}'
```

Use the returned token: `Authorization: Bearer <token>` on protected routes.

## API endpoints (summary)

| Area | Examples |
| ---- | -------- |
| Auth | `POST /api/v1/auth/register`, `POST .../login`, `GET .../me` |
| Orgs | `POST /api/v1/orgs/`, `GET /api/v1/orgs/{id}/members` |
| Intake / OAuth | `/api/v1/intake/*`, `/api/v1/intake/oauth/*` |
| Projects | `POST /api/v1/projects/` (org-scoped) |
| Graph | `GET /api/v1/projects/{id}/graph/react-flow` |
| Agents / Automations / Forge / Audit | see `/docs` |

## PDF ingestion (Sprint 6)

See `app.ingestion.parsers.common.PDFParser` — chunking, tables, AcroForm, OCR fallback.

## Integrated sprints

| Sprint | Status |
| ------ | ------ |
| 1–5 | Done |
| 6 PDF | Done |
| 7 Auth RBAC | Done |
| 8–11 | In progress |

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
