# ProjectForge AI — Roadmap

Phases are ordered by dependency. Sprints 1–7 (Phase 1–2) are **complete**.

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

Phase 2 extras: LangGraph sequential + branching, editable timeline dates, graph linking.

---

## Phase 3 — Production depth (active)

### Sprint 8: LangGraph branching — Done

- Conditional routing (`standard`, `compliance_first`, `risk_heavy`) — **Done**
- Branch path in run metadata, artifacts, and run history API — **Done**
- Orchestrator audit events (separate from compliance audit) — **Done**

### Sprint 9: Integrations hardening — Done

- Production OAuth credential gate when mock exchange disabled — **Done**
- MCP Python SDK transport (SSE + stdio) with HTTP fallback — **Done**
- Webhook connector + `POST /intake/connections/webhook/register` — **Done**

### Sprint 10: Timeline & CI — Done

- Gantt bars from `start_date` / `due_date` — **Done**
- GitHub Actions CI (backend tests + Neo4j bootstrap smoke) — **Done**
- Graph schema version bump workflow — **Next** (manual bump in `graph/bootstrap.py`)

### Sprint 11: Enterprise controls (next)

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

## Immediate next actions

1. RBAC scaffolding (Sprint 11)
2. Orchestrator audit panel in frontend
3. Webhook test delivery UI in ConnectionsPanel
4. Graph schema version bump automation in CI

See [STATUS.md](STATUS.md) and [API.md](API.md).
