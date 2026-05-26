# ProjectForge AI v14 — Status

Last updated: Sprint 23 complete on branch `cursor/sprint23-subscriptions-replica-alerts-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 161 tests
curl -s http://localhost:8000/api/v1/observability/prometheus | head
cd frontend && npm run typecheck
```

## New in Sprint 23

- **Stripe subscriptions** — recurring checkout, subscription store, webhook handlers for subscription lifecycle
- **Neo4j read replicas** — enterprise-tier tenants route graph reads to `NEO4J_READ_REPLICA_URI`
- **Alerting & runbooks** — Prometheus alert rules + on-call runbook in `deploy/observability/`

## Resume development

```bash
git checkout cursor/sprint23-subscriptions-replica-alerts-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
