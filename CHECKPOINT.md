# ProjectForge AI v14 — Checkpoint

Saved: Phase 2 starter complete on branch `cursor/sprint345-hardening-ebb0`.

## Branch chain

```
main
 └── cursor/projectforge-v14-framework-ebb0
      └── cursor/graph-editing-scheduling-ebb0
           └── cursor/neo4j-edges-attachments-ebb0
                └── cursor/sprint345-hardening-ebb0   ← current
```

## What is implemented

### Backend
- FastAPI monorepo with ingestion, graph, orchestrator, compliance, integrations, automations, workbench
- Ingestion: PDF, email, mbox, Office (tables/headings/slides), image OCR, nested attachments
- Graph: Neo4j bootstrap/migrations, orphan cleanup on rebuild, enrich + node/edge mutations
- Orchestrator: specialist agents, per-step checkpoints, run history, resume, optional LangGraph runner
- Compliance: HIPAA/legal/SOC2/GDPR profiles, redaction, audit
- Integrations: OAuth PKCE, MCP HTTP discovery, encrypted connections
- Automations: scheduling, Temporal worker, dead letters, optional Schedule sync

### Frontend
- Next.js dashboard with graph viewer (editable nodes + links), timeline dates, workbench, panels for all subsystems

## Run after restart

```bash
# Backend
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Tests
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests

# Docker full stack
docker compose up backend frontend automation-worker temporal neo4j postgres
```

## Key environment flags

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_LANGGRAPH_ORCHESTRATOR` | `false` | Run orchestrator via LangGraph StateGraph |
| `OAUTH_MOCK_TOKEN_EXCHANGE` | `true` | Mock OAuth tokens in dev |
| `TEMPORAL_SYNC_SCHEDULES` | `false` | Register Temporal Schedule API jobs |
| `NEO4J_BOOTSTRAP_ON_CONNECT` | `true` | Apply graph schema migrations on connect |
| `IMAGE_OCR_ENABLED` | `true` | Tesseract OCR for images |

## Verification at checkpoint

- Backend: **67+ tests** (`python3 -m unittest discover -s backend/app/tests`)
- Frontend: `npm run typecheck`

## Next after restart

1. Set real OAuth client credentials and disable mock exchange
2. LangGraph branching/conditional agent routing
3. Live MCP Python SDK transport
4. Production Neo4j migrations in CI

## Resume development

```bash
git checkout cursor/sprint345-hardening-ebb0
git pull origin cursor/sprint345-hardening-ebb0
```

See `docs/NEXT_SPRINTS.md` for the full roadmap.
