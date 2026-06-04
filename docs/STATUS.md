# ProjectForge AI v14 — Status

Last updated: Sprint 27 complete on branch `cursor/sprint27-scheduler-portability-autoscale-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 205 tests
curl -s -X POST http://localhost:8000/api/v1/billing/schedule/run
curl -s http://localhost:8000/api/v1/observability/autoscale
cd frontend && npm run typecheck
```

## New in Sprint 27

- **Overage billing scheduler** — `POST /api/v1/billing/schedule/run`, Helm CronJob, optional auto-invoice
- **Stripe `invoice.finalized`** — syncs local overage invoice status from Stripe webhooks
- **Tenant data portability** — export/import APIs and migrate-with-import flow for cross-region moves
- **Predictive autoscale hooks** — `GET /api/v1/observability/autoscale` and [AUTOSCALE.md](../deploy/observability/AUTOSCALE.md)

## Resume development

```bash
git checkout cursor/sprint27-scheduler-portability-autoscale-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Phase 6 (SaaS platform) is complete. See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for optional follow-ups.
