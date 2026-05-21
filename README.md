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

## Forge v0.3

| Command | Purpose |
| ------- | ------- |
| `forge validate --spec` | JSON Schema check |
| `forge run --spec` | Materialize recipe |
| `forge publish --output` | Git init, commit, optional push + draft PR (`gh`) |

## Graph / Neo4j

Set `GRAPH_BACKEND=neo4j` and `NEO4J_URI` in `.env`. `GET /health` reports graph backend status and Neo4j connectivity.

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
