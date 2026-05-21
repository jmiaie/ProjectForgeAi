# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.**

Master Build Framework v14 + **Forge CLI**.

## Highlights

- LangGraph orchestrator + specialist agents
- Postgres + Alembic, encrypted connections, audit log
- OAuth 2.0 / PKCE, multi-tenant JWT + RBAC
- **Locus + OMPA memory** — vectorless RAG retrieval + persistent session memory (Sprint 8)
- Project graph (Neo4j-ready + React Flow export)
- Automations, PDF ingestion (tables/OCR/chunking)
- Forge CLI + REST API

## Quick start

```bash
cp .env.example .env && docker-compose up -d
cd backend && pip install -r requirements.txt && python -m alembic upgrade head
uvicorn app.main:app --reload
```

```bash
npm ci && npm run build && npm test
```

## Memory API (Sprint 8)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/projects/{id}/memory/locus/index` | Index chunks into Locus |
| POST | `/api/v1/projects/{id}/memory/locus/retrieve` | Retrieve by query |
| POST | `/api/v1/projects/{id}/memory/ompa/session` | Start OMPA session |
| POST | `/api/v1/projects/{id}/memory/ompa/decisions` | Record a decision |
| GET | `/api/v1/projects/{id}/memory/ompa/history` | Session history |

Set `LOCUS_BACKEND=memory|submodule` and `OMPA_BACKEND=memory|submodule` in `.env`.

## Integrated sprints

| Sprint | Status |
| ------ | ------ |
| 1–7 | Done |
| 8 Locus/Ompa | Done |
| 9–11 | In progress |

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
