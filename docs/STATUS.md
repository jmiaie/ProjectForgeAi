# ProjectForge AI v14 — Status

Last updated: Sprint 24 complete on branch `cursor/sprint24-portal-cluster-slo-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 173 tests
curl -s http://localhost:8000/api/v1/observability/slo
curl -s http://localhost:8000/api/v1/neo4j/cluster/status
cd frontend && npm run typecheck
```

## New in Sprint 24

- **Stripe customer portal** — `POST /billing/portal` and subscription cancellation UI/API
- **Neo4j cluster failover** — health checks, URI failover, `GET /neo4j/cluster/status`
- **SLO dashboards** — `GET /observability/slo`, SLO Grafana dashboard, error-budget alerts

## Resume development

```bash
git checkout cursor/sprint24-portal-cluster-slo-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
