# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.** Upload all project documents once → instant living project graph → auto-generates every template, contract, schedule, automation, communication loop, and compliance control.

This repository implements the **Master Build Framework v14**, plus a **Forge CLI** for spec-driven repository scaffolding.

---

## Highlights

- **Industry-agnostic** PM framework that adapts from solopreneur gigs to enterprise programs.
- **100% accuracy grounding** via Locus (vectorless RAG) + OMPA (persistent memory) + Neo4j project graph.
- **LLM-flexible** by design: low-cost defaults, flagship upsell, and full Bring-Your-Own-Key via LiteLLM.
- **Intake / Connections Wizard** with OAuth 2.0 / PKCE, API keys, webhooks, and MCP tool discovery.
- **Compliance-first**: HIPAA, SOC 2, GDPR, legal modes — with self-improvement gated by category.
- **Forge CLI** — versioned recipes produce reproducible project trees locally (see below).
- **Parallel-build ready**: scaffolded so Cursor, Claude, Grok, Lovable and Manus can ship in parallel.

## Repository layout

```
├── backend/           # FastAPI — agents, ingestion, integrations, storage adapters
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
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Quick start — Forge CLI

**Requirements:** Node.js 20+

```bash
npm ci
npm run build
npm test
npm run forge -- list
npm run forge -- run --recipe minimal --output ./my-new-project --name my-app
```

With a JSON spec:

```bash
npm run forge -- run --recipe express-api --spec ./examples/specs/api-service.json --output ./api-out
npm run forge -- validate --spec ./examples/specs/api-service.json
```

| Doc | Description |
|-----|-------------|
| [docs/vision.md](docs/vision.md) | Forge vision & v1 scope |
| [docs/architecture.md](docs/architecture.md) | Forge components |
| [docs/adr/001-execution-model.md](docs/adr/001-execution-model.md) | Safety defaults |

## Key API endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/health` | Liveness + version |
| GET | `/api/v1/intake/connectors` | List connectors per tier |
| POST | `/api/v1/intake/connections` | Authenticate + persist connector |
| POST | `/api/v1/projects/` | Create project, ingest files, plan agents |

## Phase roadmap

| Phase | Status | Focus |
| ----- | ------ | ----- |
| v14 scaffold | Done | Backend, frontend, docker-compose |
| Forge v0.1 | Done | `minimal` recipe, manifest, ADR-001 |
| Forge v0.2 | Done | JSON spec, `express-api` recipe, `validate` |
| Sprint 1+ | Branches | LangGraph, persistence, OAuth, graph, … (see open PRs) |

## Parallel development

| Tool | Focus |
| ---- | ----- |
| Cursor | Integration, forge CLI, git workflow |
| Claude Opus | LangGraph orchestrator & specialist agents |
| Grok | Master framework coordination |
| Lovable | Full-stack UI |
| Manus | OAuth, MCP, ingestion testing |

## License

Platform components: proprietary — ProjectForge AI. Forge CLI tooling: MIT — see [LICENSE](LICENSE).
