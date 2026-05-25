# ProjectForge AI — Agent Handoff (v14)

Copy this document into Claude, Cursor, Lovable, Manus, or other coding agents as the parallel-development brief.

## Vision

**ProjectForge AI** — upload all project documents once, get an instant living project graph, auto-generate templates, schedules, automations, communications, and compliance controls.

- Industry-agnostic (construction anchor; software, legal, healthcare, events, M&A)
- Solopreneur-friendly through enterprise RBAC/audit/on-prem
- LLM: low-cost default via LiteLLM, flagship upsell, BYO keys
- Integrations: OAuth 2.0/PKCE, API keys, webhooks, MCP
- Compliance-first: HIPAA priority + modular SOC 2, GDPR, legal

## Architecture (summary)

```text
Upload + Intake → Ingestion → Locus + OMPA + Neo4j graph
    → Orchestrator (LangGraph) + specialists → LLM Router
    → Compliance + audit → Temporal automations → Next.js dashboard
```

Full diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Tech stack

| Layer | Stack |
|-------|-------|
| Backend | FastAPI, LangGraph, Temporal.io (Python 3.12) |
| LLM | LiteLLM (+ Ollama local) |
| Storage | Locus, OMPA, Neo4j, PostgreSQL |
| Integrations | Authlib OAuth, MCP Python SDK |
| Frontend | Next.js 15, TypeScript, React Flow, Tailwind |
| Deploy | Docker Compose; hybrid/on-prem manifests planned |

## Repository map

```text
backend/app/
  agents/           orchestrator.py, langgraph_runner.py, run_store.py, tools.py
  graph/            adapter, builder, enricher, mutations, bootstrap, extraction
  ingestion/        pipeline, attachments, parsers/common/*
  integrations/     intake_form, registry, connectors/oauth.py, connectors/mcp.py
  automations/      service, scheduling, temporal_*, worker_main.py
  compliance/       enforcer, redaction, audit
  workbench/        service.py
  storage/          locus_adapter, ompa_adapter, native_loader
  main.py           FastAPI entry + route registration

frontend/
  app/              dashboard + settings/connections
  components/       GraphPanel, TimelinePanel, OrchestratorPanel, etc.
  lib/api.ts        typed API client
```

## Conventions

1. **Config** — all flags in `core/config.py` + `.env.example`; never hardcode secrets.
2. **Graph** — mutations go through `graph/mutations.py`; adapter handles Neo4j vs memory.
3. **Compliance** — gate LLM calls and external writes via `compliance/enforcer.py`.
4. **Tests** — `backend/app/tests/` with unittest; run with `PYTHONPATH=backend/app`.
5. **Frontend** — call backend via `lib/api.ts`; default project `NEXT_PUBLIC_DEFAULT_PROJECT_ID`.

## Native Locus + OMPA

```env
LOCUS_SOURCE_PATH=/path/to/locus
OMPA_SOURCE_PATH=/path/to/ompa
REQUIRE_NATIVE_LOCUS_OMPA=true
```

Without native packages, dev fallbacks activate (reported on `/health`).

## Key feature flags

| Flag | Purpose |
|------|---------|
| `USE_LANGGRAPH_ORCHESTRATOR` | LangGraph with conditional branching |
| `USE_LANGGRAPH_BRANCHING` | Route specialists after intake by goal/graph density |
| `OAUTH_MOCK_TOKEN_EXCHANGE` | Dev OAuth without real client credentials |
| `TEMPORAL_SYNC_SCHEDULES` | Register schedules with Temporal API |
| `NEO4J_BOOTSTRAP_ON_CONNECT` | Auto-apply graph migrations |
| `IMAGE_OCR_ENABLED` | Tesseract for image uploads |

## Current phase

**Phase 3** — production depth: LangGraph branching, real OAuth, MCP SDK, Gantt bars, CI migrations.

Roadmap: [docs/NEXT_SPRINTS.md](docs/NEXT_SPRINTS.md)  
Status: [docs/STATUS.md](docs/STATUS.md)  
API: [docs/API.md](docs/API.md)

## Agent roles

- **Cursor** — integration, git, CI, local run verification
- **Claude** — orchestrator/LangGraph, specialist agents
- **Lovable** — dashboard UX, templates, timeline
- **Manus** — OAuth/MCP/ingestion E2E tests
- **Grok** — framework coordination and product framing

## Do not regenerate

These modules exist and are tested — extend, do not replace from scratch:

- `graph/bootstrap.py`, `automations/temporal_schedules.py`, `ingestion/attachments.py`
- Full ingestion parser suite, orchestrator run store, OAuth PKCE state store

When adding endpoints, register in `main.py` or `integrations/intake_form.py` and document in `docs/API.md`.
