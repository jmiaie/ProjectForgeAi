# ProjectForge AI — Roadmap

Phases 1–6 through Sprint 25 are **complete**. Sprint 26 is **complete**.

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

---

## Immediate next actions

1. Automated overage invoice scheduling (cron + Stripe finalize webhooks)
2. Tenant data export/import for cross-region migrations
3. Predictive autoscaling hooks from capacity API

See [STATUS.md](STATUS.md) and [API.md](API.md).
