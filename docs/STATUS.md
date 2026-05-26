# ProjectForge AI v14 — Status

Last updated: Sprint 25 complete on branch `cursor/sprint25-metering-region-heal-ebb0`.

## Verification

```bash
PYTHONPATH=backend/app python3 -m unittest discover -s backend/app/tests   # 184 tests
curl -s http://localhost:8000/api/v1/regions
curl -s http://localhost:8000/api/v1/tenants/tenant_default/billing/overage
cd frontend && npm run typecheck
```

## New in Sprint 25

- **LLM overage metering** — Stripe meter events for token overages, overage API, report action in billing UI
- **Neo4j K8s auto-heal** — cluster heal endpoint, Helm CronJob, operator guide in `deploy/neo4j/K8S_AUTOHEAL.md`
- **Multi-region routing** — tenant region assignment, residency validation, regions catalog API

## Resume development

```bash
git checkout cursor/sprint25-metering-region-heal-ebb0
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

See [NEXT_SPRINTS.md](NEXT_SPRINTS.md) for follow-up priorities.
