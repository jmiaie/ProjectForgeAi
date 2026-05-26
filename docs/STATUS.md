# ProjectForge AI v14 — Status

Last updated: Sprint 22 complete on branch `cursor/sprint22-webhooks-neo4j-cloud-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 153 tests
curl -s http://localhost:8000/api/v1/observability/prometheus | head
cd frontend && npm run typecheck
```

## New in Sprint 22

- **Stripe webhooks** — `POST /api/v1/billing/webhook` for `checkout.session.completed` and `invoice.paid`; signature verification; tier upgrade on payment
- **Neo4j auto-provision** — `NEO4J_AUTO_PROVISION_DATABASES` creates Enterprise databases and bootstraps schema per tenant
- **Grafana Cloud guide** — `deploy/observability/GRAFANA_CLOUD.md` for Alloy/agent remote-write wiring

## Resume development

```bash
git checkout cursor/sprint22-webhooks-neo4j-cloud-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
