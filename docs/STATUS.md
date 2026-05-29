# ProjectForge AI v14 — Status

Last updated: Sprint 26 complete on branch `cursor/sprint26-invoice-migrate-capacity-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 193 tests
curl -s http://localhost:8000/api/v1/observability/capacity
curl -s -X POST http://localhost:8000/api/v1/tenants/tenant_default/billing/overage/invoice
cd frontend && npm run typecheck
```

## New in Sprint 26

- **Overage invoice line items** — Stripe invoices with LLM overage line items from usage reports
- **Region migration** — cross-region read replica routing and tenant migration API
- **Capacity planning** — `/observability/capacity` API and Grafana capacity dashboard

## Resume development

```bash
git checkout cursor/sprint26-invoice-migrate-capacity-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
