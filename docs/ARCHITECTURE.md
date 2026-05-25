# ProjectForge AI — Architecture

## Data flow

```text
Upload / Intake Wizard (OAuth · API key · MCP)
        ↓
Ingestion parsers → Locus.index + OMPA.record + manifest JSON
        ↓
Graph builder → Neo4j (or in-memory) project graph
        ↓
Orchestrator (LangGraph optional) + specialist agents
        ↓
LLM Router (LiteLLM) with compliance redaction
        ↓
Compliance enforcer + audit trail
        ↓
Temporal automations (reminders, reports, sync jobs)
        ↓
Next.js dashboard (React Flow, timeline, workbench)
```

Per-project isolation: dedicated Locus store, OMPA vault, graph partition, encrypted connection tokens.

## Backend packages

```text
backend/app/
├── ingestion/       pipeline, manifest, parsers (pdf, email, mbox, office, image), attachments
├── graph/           adapter, builder, enricher, extraction, mutations, bootstrap
├── agents/          orchestrator, langgraph_runner, run_store, tools, state
├── compliance/      enforcer, redaction, audit
├── integrations/    registry, intake_form, oauth_state_store, connectors (oauth, mcp)
├── automations/     service, store, scheduling, temporal_worker/workflows/activities
├── workbench/       Locus + graph query service
├── storage/         locus_adapter, ompa_adapter, rtk_adapter, native_loader
└── core/            config, llm_router, integrations_manager
```

## Graph schema (starter)

**Labels:** Project, Document, Chunk, Stakeholder, Task, Milestone, Risk, Decision

**Edges:** HAS_DOCUMENT, HAS_CHUNK, DERIVED_FROM, RELATES_TO, DEPENDS_ON

Bootstrap applies constraints/indexes via `graph/bootstrap.py` (`SCHEMA_VERSION=2`).

## Orchestrator routing

Default specialist sequence: intake_analyst → scheduler → risk_analyst → compliance_reviewer → template_generator.

When `USE_LANGGRAPH_ORCHESTRATOR=true`, a router after intake selects one of:

- **standard** — default order above
- **compliance_first** — compliance before scheduling (HIPAA/legal goals)
- **risk_heavy** — risk before schedule (empty or sparse graph)

Checkpoints persist after each step via `OrchestratorRunStore`.

## Storage fallbacks

| Component | Production | Dev fallback |
|-----------|------------|--------------|
| Locus/OMPA | Native packages via `LOCUS_SOURCE_PATH` / `OMPA_SOURCE_PATH` | In-memory adapters |
| Neo4j | Bolt driver | In-memory graph adapter |
| Temporal | Worker + schedules | Local automation dispatch |

## Frontend

Next.js 15 App Router. API client in `frontend/lib/api.ts` targeting `NEXT_PUBLIC_API_BASE_URL`. Main dashboard composes panel components; connections wizard at `app/settings/connections`.

## Deployment modes

`DEPLOYMENT_MODE`: `saas` (default), `hybrid`, `onprem`. Docker Compose runs the full stack for local and hybrid dev.
