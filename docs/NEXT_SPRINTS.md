# ProjectForge AI — Roadmap

Phases are ordered by dependency. Sprints 1–16 are **complete**. Phase 5 Sprint 17 is **complete**.

## Phase 4 — Domain expansion (complete)

| Sprint | Scope | Status |
|--------|-------|--------|
| 12 Portfolio | Project registry, switcher, cross-project summaries | Done |
| 13 Ingestion | CAD/BIM stubs, codebase archives, PostgreSQL schema | Done |
| 14 LLM & billing | Flagship routing, BYO keys, usage metering | Done |
| 15 RTK spatial | Geo assets, graph sync, map view | Done |

---

## Phase 5 — Enterprise GA (complete)

### Sprint 16: Identity & deploy (complete)

- SSO/OIDC identity provider scaffolding
- Kubernetes Helm chart (alongside Compose overlay)
- SOC 2 control mapping export starter

### Sprint 17: Portfolio intelligence (complete)

- Cross-project risk/compliance rollups
- Portfolio-level orchestrator runs
- Executive dashboard widgets

---

## Immediate next actions

1. Air-gapped update bundle workflow
2. Production hardening pass (auth enforcement, ingress TLS defaults)
3. End-to-end portfolio intelligence smoke in CI

See [STATUS.md](STATUS.md) and [API.md](API.md).
