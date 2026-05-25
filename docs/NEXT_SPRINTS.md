# ProjectForge AI — Roadmap

Phases are ordered by dependency. Sprints 1–7 (Phase 1–2) are **complete** unless noted.

## Phase 1–2 (complete)

| Sprint | Scope | Status |
|--------|-------|--------|
| 1 Ingestion | PDF, email, mbox, Office, OCR, attachments, upload, manifest | Done |
| 2 Graph | Schema, Neo4j bootstrap/migrations, enrich, mutations, orphan cleanup | Done |
| 3 Orchestrator | Specialists, checkpoints, run history, resume, LangGraph runner | Done |
| 4 Compliance | Profiles, redaction, gates, audit | Done |
| 5 Integrations | OAuth PKCE, encrypted storage, MCP HTTP discovery, health UI | Done |
| 6 Frontend | Dashboard, editable graph, timeline, workbench, panels | Done |
| 7 Temporal | Worker, scheduling, approvals, dead letters, Schedule sync | Done |

Phase 2 extras delivered: LangGraph sequential runner, editable timeline dates, graph DEPENDS_ON/RELATES_TO linking.

---

## Phase 3 — Production depth (active)

### Sprint 8: LangGraph branching

**Status:** In progress. Conditional routing after intake based on goal keywords and graph density.

- Sequential StateGraph runner — **Done**
- Router node with `compliance_first`, `risk_heavy`, `standard` paths — **Done (Phase 3 kickoff)**
- Orchestrator audit events separate from compliance audit — **Next**
- Expose branch decision in run artifacts / API — **Next**

### Sprint 9: Integrations hardening

- Real Google/Microsoft OAuth credentials; disable `OAUTH_MOCK_TOKEN_EXCHANGE` — **Next**
- Live MCP Python SDK transport (stdio/SSE) alongside HTTP fallback — **Next**
- Webhook connector type in registry — **Next**

### Sprint 10: Timeline & CI

- Gantt bars computed from `start_date` / `due_date` on graph nodes — **In progress**
- Neo4j migration smoke test in CI (GitHub Actions) — **Next**
- Graph schema version bump workflow — **Next**

### Sprint 11: Enterprise controls

- RBAC scaffolding for project-scoped actions
- Self-improver / upgrade manager gates wired to compliance category
- On-prem deployment manifest (K8s/Compose prod overlays)

---

## Phase 4 — Domain expansion (planned)

- CAD/BIM and codebase ingestion adapters
- RTK spatial layer integration
- Multi-project portfolio dashboard
- Flagship LLM upsell routing and BYO key management UI

---

## Parallel agent assignments

| Agent | Focus |
|-------|-------|
| Cursor | Integration, git, CI, frontend polish |
| Claude | LangGraph depth, specialist agent logic |
| Lovable | Dashboard UX, templates, Gantt |
| Manus | OAuth/MCP E2E tests, ingestion smoke |

## Immediate next actions

1. Finish Gantt date-based bar layout in `TimelinePanel`
2. Wire orchestrator branch metadata into run API response
3. Add webhook connector stub + intake form route
4. CI job: `unittest` + Neo4j bootstrap smoke on push

See [STATUS.md](STATUS.md) for verification commands and [API.md](API.md) for endpoints.
