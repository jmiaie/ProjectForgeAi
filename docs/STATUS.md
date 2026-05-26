# ProjectForge AI v14 — Status

Last updated: Sprint 20 complete on branch `cursor/sprint20-otel-billing-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 139 tests
python3 scripts/smoke_portfolio_intelligence.py
curl -s http://localhost:8000/api/v1/observability/prometheus | head
cd frontend && npm run typecheck
```

## New in Sprint 20

- **OTel export bridges** — Prometheus text format, Jaeger and OTLP trace JSON endpoints
- **Tenant billing** — usage store, tier quotas, billing check/usage/quota APIs
- **Quota enforcement** — project registration blocked when tenant exceeds limits
- **GPG key rotation** — runbook and `rotate_airgap_gpg_key.py` helper
- **TenantBillingPanel** — quota widget on portfolio page

## Resume development

```bash
git checkout cursor/sprint20-otel-billing-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
