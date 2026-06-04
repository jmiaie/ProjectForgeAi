# ProjectForge AI — Roadmap

Phases 1–6 through Sprint 27 are **complete**. Phase 6 (SaaS platform) is finished.

## Phase 6 — SaaS platform (complete)

| Sprint | Scope | Status |
|--------|-------|--------|
| 19 SaaS platform | GPG bundles, tenant isolation, observability | Done |
| 20 SaaS ops | OTel export, tenant billing quotas, GPG rotation | Done |
| 21 SaaS scale | Grafana dashboards, Stripe billing, Neo4j tenant DBs | Done |
| 22 SaaS production | Stripe webhooks, Neo4j auto-provision, Grafana Cloud guide | Done |
| 23 SaaS enterprise | Stripe subscriptions, Neo4j read replicas, alerting runbooks | Done |
| 24 SaaS reliability | Stripe customer portal, Neo4j cluster failover, SLO dashboards | Done |
| 25 SaaS scale-out | LLM overage metering, Neo4j K8s auto-heal, multi-region routing | Done |
| 26 SaaS billing ops | Overage invoice line items, region migration, capacity planning | Done |
| 27 SaaS automation | Overage billing scheduler, tenant export/import, autoscale hooks | Done |

---

## Post–Phase 6 ideas

Future work may extend beyond the original SaaS roadmap:

1. Frontend controls for billing schedule and tenant export/import
2. HPA operator or GitOps controller wired to `/observability/autoscale`
3. Full Neo4j graph payload in tenant export bundles (currently metadata-focused)

See [STATUS.md](STATUS.md) and [API.md](API.md).
