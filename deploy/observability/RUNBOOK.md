# ProjectForge on-call runbook

Operational procedures for Grafana alerts defined in `grafana/alerts/projectforge-alerts.yaml`.

## Quick checks

```bash
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/api/v1/observability/prometheus | head
curl -sf http://localhost:8000/api/v1/deploy/status
```

## High error rate

**Alert:** `ProjectForgeHighErrorRate`

1. Open Grafana → **ProjectForge overview** dashboard → confirm 5xx panel spike.
2. Inspect recent traces: `GET /api/v1/observability/traces/jaeger?limit=20`
3. Check backend logs for stack traces around the time of the alert.
4. Common causes:
   - Neo4j connectivity loss → verify `NEO4J_URI`, fallback to in-memory if acceptable temporarily
   - Tenant quota enforcement returning 403/429 → review `/api/v1/tenants/{id}/billing/quota`
   - Unhandled integration timeouts → check Temporal worker and external OAuth endpoints
5. Mitigation: scale backend replicas, restart unhealthy pods, disable failing feature flag if needed.

## High latency

**Alert:** `ProjectForgeHighLatency`

1. Identify hot routes in the dashboard **Top routes** panel.
2. If graph reads dominate and tenant is enterprise-tier, confirm read-replica routing:
   - `NEO4J_READ_REPLICA_ENABLED=true`
   - `GET /api/v1/tenants/{id}/status` → `neo4j.read_replica_enabled`
3. Check LLM routing latency if orchestrator routes are slow.
4. Mitigation: increase backend CPU/memory, enable read replica, reduce orchestrator concurrency.

## No traffic

**Alert:** `ProjectForgeNoTraffic`

1. Verify ingress/load balancer routes to the backend Service.
2. Confirm Prometheus/Alloy scrape target is reachable (`prometheus-scrape.yml`).
3. Run a synthetic request: `curl -sf http://backend:8000/health`
4. If health OK but metrics flat → scraper misconfiguration; see [GRAFANA_CLOUD.md](GRAFANA_CLOUD.md).

## Metrics missing

**Alert:** `ProjectForgeMetricsMissing`

1. Confirm env flags:
   ```env
   OTEL_EXPORTER_ENABLED=true
   OBSERVABILITY_ENABLED=true
   METRICS_ENABLED=true
   ```
2. Hit metrics endpoint directly from the scraper host.
3. Reload Prometheus/Alloy config after fixing scrape targets.
4. Import alert rules: upload `grafana/alerts/projectforge-alerts.yaml` in Grafana → Alerting → Import.

## Billing / subscription incidents

1. Check provider status: `GET /api/v1/billing/status`
2. Review Stripe webhook delivery in the Stripe dashboard.
3. For stuck tiers after payment, replay webhook payload to `POST /api/v1/billing/webhook` (mock mode in dev).
4. Verify subscription record: `GET /api/v1/tenants/{id}/billing/subscription`

## Escalation

| Severity | Response |
|----------|----------|
| critical | Page on-call engineer; consider rollback if error rate persists >15m |
| warning | Investigate within business hours; document in incident channel |

## Related docs

- [README.md](README.md) — self-hosted Prometheus/Grafana
- [GRAFANA_CLOUD.md](GRAFANA_CLOUD.md) — managed Prometheus remote-write
