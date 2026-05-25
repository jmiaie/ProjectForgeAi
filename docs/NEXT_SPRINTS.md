# ProjectForge AI — Roadmap

Phases are ordered by dependency. Sprints 1–13 are **complete**.

## Phase 4 — Domain expansion (active)

### Sprint 12: Multi-project portfolio — Done

- Project registry, portfolio summary API, project switcher UI — **Done**

### Sprint 13: Ingestion expansion — Done

- CAD/BIM stubs, codebase archives, PostgreSQL schema intake — **Done**

### Sprint 14: LLM & billing — Done

- Flagship model upsell routing in LLMRouter — **Done**
- BYO API key storage and management UI — **Done**
- Per-project LLM usage metering — **Done**

### Sprint 15: RTK spatial layer — Next

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

1. RTK spatial adapter stub (Sprint 15)
2. Map view for geo-tagged graph nodes
3. Helm chart from on-prem Compose manifest
4. SSO/OIDC identity provider scaffolding

See [STATUS.md](STATUS.md) and [API.md](API.md).
