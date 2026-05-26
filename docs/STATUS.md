# ProjectForge AI v14 — Status

Last updated: Sprint 21 complete on branch `cursor/sprint21-grafana-stripe-neo4j-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 146 tests
curl -s http://localhost:8000/api/v1/observability/prometheus | head
cd frontend && npm run typecheck
```

## New in Sprint 21

- **Grafana/Prometheus** — dashboard JSON + scrape config in `deploy/observability/`
- **Stripe billing** — mock/real checkout, invoice store, billing APIs
- **Neo4j tenant isolation** — per-tenant database routing and property scoping
- **TenantBillingPanel** — checkout action on portfolio page

## Resume development

```bash
git checkout cursor/sprint21-grafana-stripe-neo4j-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
