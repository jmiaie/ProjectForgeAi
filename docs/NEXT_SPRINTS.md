# ProjectForge AI — Roadmap

Phases are ordered by dependency. Sprints 1–11 (Phase 3) are **complete**.

## Phase 3 (complete)

| Sprint | Scope | Status |
|--------|-------|--------|
| 8 LangGraph branching | Conditional routing, orchestrator audit, branch in API | Done |
| 9 Integrations | OAuth prod gate, MCP SDK, webhook connector | Done |
| 10 Timeline & CI | Date-based Gantt, GitHub Actions, schema version check | Done |
| 11 Enterprise | RBAC, upgrade manager, on-prem overlay, access UI | Done |

---

## Phase 4 — Domain expansion (active)

### Sprint 12: Multi-project portfolio — Done

- Project registry, portfolio summary API, project switcher UI — **Done**

### Sprint 13: Ingestion expansion — Done

- CAD/BIM adapter stubs (IFC, DWG metadata) — **Done**
- Codebase archive ingestion (zip/tar) — **Done**
- PostgreSQL schema snapshot intake — **Done**

### Sprint 14: LLM & billing — Next

- Flagship model upsell routing in LLMRouter
- BYO API key management UI
- Usage metering hooks per project

### Sprint 15: RTK spatial layer

- RTK adapter wiring for geo-tagged project assets
- Map view in frontend for construction anchor workflows

---

## Phase 5 — Enterprise GA (planned)

- Full RBAC with SSO/OIDC identity provider
- SOC 2 control mapping export
- Kubernetes Helm chart (alongside Compose overlay)
- Air-gapped update bundle workflow

---

## Immediate next actions

1. Flagship model upsell routing in LLMRouter (Sprint 14)
2. BYO API key management UI
3. Usage metering hooks per project
4. Helm chart from on-prem Compose manifest

See [STATUS.md](STATUS.md) and [API.md](API.md).
