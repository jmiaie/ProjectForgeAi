# ProjectForge SLO definitions

Service level objectives for ProjectForge AI backend (`projectforge-ai`).

## Targets

| SLO | Target | Measurement |
|-----|--------|-------------|
| Availability | 99.9% | `1 - (5xx errors / total requests)` |
| Latency (avg) | ≤ 750 ms | `projectforge_http_request_duration_ms_avg` |

Configure via environment:

```env
SLO_AVAILABILITY_TARGET=0.999
SLO_LATENCY_MS_TARGET=750
```

## Error budget

For 99.9% availability, the **allowed error rate** is **0.1%** of requests.

Error budget remaining:

```
remaining = 1 - (actual_error_rate / allowed_error_rate)
```

- **> 50%** — healthy
- **≤ 50%** — burning (warning)
- **≤ 0%** — exhausted (page on-call)

### Error budget

When `ProjectForgeErrorBudgetBurn` fires:

1. Check `GET /api/v1/observability/slo` for current burn rate.
2. Open the **ProjectForge SLO Overview** dashboard.
3. Correlate with deployment changes and top error routes.
4. Follow [RUNBOOK.md](RUNBOOK.md#high-error-rate) for mitigation.

## Latency SLO

When `ProjectForgeSLOLatencyBreach` fires:

1. Inspect top routes panel in Grafana.
2. For enterprise tenants, verify Neo4j read-replica routing is active.
3. Check orchestrator/LLM latency if agent routes dominate.

## API

Live SLO snapshot (in-process metrics):

```
GET /api/v1/observability/slo
```

## Dashboard

Import `grafana/dashboards/projectforge-slo.json` alongside the main overview dashboard.

Alert rules in `grafana/alerts/projectforge-alerts.yaml` include error-budget and latency SLO breaches.
