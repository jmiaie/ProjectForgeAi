# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.**

Master Build Framework v14 + **Forge CLI** (v0.3).

## Highlights

- LangGraph orchestrator, Postgres, OAuth, JWT + RBAC
- Locus + OMPA memory, project graph (Neo4j-ready)
- Automations, PDF/CAD/repo ingestion
- **Forge CLI** — spec → scaffold → `forge publish` (git + draft PR)
- **Frontend** — intake wizard, projects list, React Flow graph viewer
- Helm + production Docker Compose

## Quick start

```bash
cp .env.example .env && docker-compose up -d
cd backend && pip install -r requirements.txt && python -m alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
# http://localhost:3000/projects
```

```bash
npm ci && npm run build && npm test
npm run forge -- run --spec ./examples/specs/api-service.json --output ./api-out
npm run forge -- publish --output ./api-out --push --remote git@github.com:you/repo.git
```

## Golden path: intake → orchestration → Forge output

The end-to-end flow connects project intake through agent orchestration to a
reviewable Forge run persisted against the project record.

```
POST /api/v1/projects/          ← create project (ingest docs, orchestrate)
POST /api/v1/forge/runs         ← create & run a Forge recipe against the project
GET  /api/v1/forge/runs/{id}    ← poll status (pending → running → completed/failed)
GET  /api/v1/forge/runs?project_id=  ← list all runs for a project
```

### Example: run a recipe from the API

```bash
# 1. Create a project
PROJECT_ID=$(curl -s -X POST http://localhost:8000/api/v1/projects/ \
  -F name=my-api -F compliance=standard | jq -r .project_id)

# 2. Start a Forge run (returns 202 with completed run)
curl -s -X POST http://localhost:8000/api/v1/forge/runs \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"spec\":{\"projectName\":\"my-api\",\"recipe\":\"express-api\",\"port\":3000}}" \
  | jq .
```

The response includes `status`, `recipe_id`, `recipe_version`, `manifest` (with
generated file list), and `error` if the run failed.

### Approve and publish (CLI — explicit action required)

Generated output is never automatically pushed. To publish a scaffold after
reviewing:

```bash
npm run forge -- run --spec ./examples/specs/api-service.json --output ./api-out
npm run forge -- publish --output ./api-out --branch forge/my-api
```

## Forge v0.3

| Command | Purpose |
| ------- | ------- |
| `forge validate --spec` | JSON Schema check |
| `forge run --spec` | Materialize recipe |
| `forge publish --output` | Git init, commit, optional push + draft PR (`gh`) |

### Forge reliability

- **Unresolved template variables fail loudly** — `{{unknownVar}}` in a template
  raises an error rather than silently becoming an empty string.
- **Path-safety checks** — generated output paths are verified to stay within
  the output directory; traversal attempts raise an error.

## Production configuration (`APP_ENV=production`)

Set `APP_ENV=production` to activate fail-closed startup checks:

| Rejected value | Setting |
|---|---|
| `*` wildcard | `ALLOWED_ORIGINS` |
| `dev-only-jwt-secret-change-me` | `JWT_SECRET` |
| `dev-only-not-secure-change-me` | `ENCRYPTION_KEY` |
| `true` | `AUTO_CREATE_SCHEMA` |

Development and test environments are unaffected. Errors are actionable and
raised at startup (via `validate_production_settings` in
`backend/app/core/config.py`).

### New environment variables

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | Deployment environment (`development`, `test`, `staging`, `production`) |

## Graph / Neo4j

Set `GRAPH_BACKEND=neo4j` and `NEO4J_URI` in `.env`. `GET /health` reports graph backend status and Neo4j connectivity.

## Local test commands

```bash
# Backend (Python)
cd backend
DATABASE_URL=sqlite+aiosqlite:///./test.db \
ENCRYPTION_KEY=test-only-not-secure \
AUTO_CREATE_SCHEMA=true \
GRAPH_BACKEND=memory \
python -m pytest tests/ -q

# Backend lint (Ruff)
python -m ruff check app tests

# Forge CLI (TypeScript)
cd ..
npm ci
npm run lint     # TypeScript type-check
npm run build
npm test

# Forge smoke
npm run forge -- validate --spec ./examples/specs/api-service.json
npm run forge -- run --recipe minimal --output /tmp/smoke-out --name smoke-test
```

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
