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
