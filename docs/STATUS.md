# ProjectForge AI v14 — Status

Last updated: Phase 3 kickoff on branch `cursor/docs-phase3-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 72 tests
cd frontend && npm run typecheck
curl http://localhost:8000/health
```

## Backend modules

| Module | Status |
|--------|--------|
| Ingestion pipeline | PDF, EML, mbox, Office, OCR, nested attachments, manifest |
| Graph builder | Manifest projection, LLM enrich, mutations, rebuild + orphan cleanup |
| Neo4j adapter | Versioned bootstrap (`SCHEMA_VERSION=2`), in-memory fallback |
| Orchestrator | Specialist agents, per-step checkpoints, run history, resume |
| LangGraph runner | Optional sequential + conditional branching (`USE_LANGGRAPH_ORCHESTRATOR`) |
| Compliance | Profiles, redaction, memory/external-write gates, audit |
| Integrations | OAuth PKCE, encrypted storage, MCP HTTP discovery |
| Automations | Local store, scheduling, Temporal worker, dead letters |

## Frontend panels

Upload, graph build/enrich/edit, timeline/Gantt, workbench, orchestrator (artifacts + history), compliance, connections (live health), automations (approve/history/temporal).

## Resume development

```bash
git checkout cursor/docs-phase3-ebb0
git pull origin cursor/docs-phase3-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for Phase 3 priorities.
