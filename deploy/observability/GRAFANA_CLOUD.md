# Grafana Cloud & managed Prometheus

Wire ProjectForge AI metrics into Grafana Cloud or any hosted Prometheus-compatible backend.

## Prerequisites

- ProjectForge backend reachable over HTTPS (or via agent/tunnel in dev)
- Grafana Cloud account ([grafana.com/products/cloud](https://grafana.com/products/cloud)) **or** another managed Prometheus endpoint

Enable metrics export on the backend:

```env
OTEL_EXPORTER_ENABLED=true
OBSERVABILITY_ENABLED=true
METRICS_ENABLED=true
OTEL_EXPORTER=prometheus
OTEL_PROMETHEUS_PATH=/api/v1/observability/prometheus
```

Verify locally:

```bash
curl -s http://localhost:8000/api/v1/observability/prometheus | head
```

## Option A — Grafana Alloy / Agent scrape (recommended)

Grafana Alloy (or Grafana Agent) scrapes your ProjectForge `/api/v1/observability/prometheus` endpoint and remote-writes to Grafana Cloud.

1. In Grafana Cloud → **Connections** → **Add new connection** → **Prometheus** → copy the remote-write URL and credentials.
2. Install Alloy on the same network as ProjectForge (or use a sidecar in Kubernetes).

Example `config.alloy`:

```hcl
prometheus.scrape "projectforge" {
  targets = [{ __address__ = "backend:8000" }]
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
  metrics_path = "/api/v1/observability/prometheus"
  scrape_interval = "30s"
}

prometheus.remote_write "grafana_cloud" {
  endpoint {
    url = "https://prometheus-prod-XX-prod-XX-zone.grafana.net/api/prom/push"
    basic_auth {
      username = "<grafana-cloud-instance-id>"
      password = "<grafana-cloud-api-token>"
    }
  }
}
```

3. Start Alloy: `alloy run config.alloy`
4. In Grafana Cloud → **Explore** → select your Prometheus datasource → query `projectforge_http_requests_total`.

## Option B — Kubernetes ServiceMonitor + Grafana Cloud

If you deploy with Helm and run Prometheus Operator in-cluster:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: projectforge
  labels:
    release: kube-prometheus-stack
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: projectforge
  endpoints:
    - port: http
      path: /api/v1/observability/prometheus
      interval: 30s
```

Configure your in-cluster Prometheus `remote_write` to Grafana Cloud (same URL/credentials as Option A).

## Option C — Direct remote-write adapter

For environments without Alloy, run the [Prometheus remote-write adapter](https://github.com/prometheus/prometheus/tree/main/documentation/examples/remote_storage) or `prometheus-adapter` sidecar that scrapes ProjectForge and forwards to Grafana Cloud.

Minimal scrape + remote_write snippet for a standalone Prometheus:

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: projectforge
    metrics_path: /api/v1/observability/prometheus
    static_configs:
      - targets: ['backend:8000']

remote_write:
  - url: https://prometheus-prod-XX-prod-XX-zone.grafana.net/api/prom/push
    basic_auth:
      username: "<grafana-cloud-instance-id>"
      password: "<grafana-cloud-api-token>"
```

## Import the dashboard

1. Grafana Cloud → **Dashboards** → **Import**
2. Upload `grafana/dashboards/projectforge-overview.json` from this repo
3. Select your Grafana Cloud Prometheus datasource

Panels cover HTTP rate, latency, top routes, and 5xx errors.

## Security notes

- Prefer private networking or mTLS between scraper and ProjectForge in production.
- Do not expose `/api/v1/observability/prometheus` publicly without authentication; use Alloy on a trusted network or protect with an ingress allowlist.
- Rotate Grafana Cloud API tokens on the same cadence as other infrastructure secrets.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No metrics in Grafana Cloud | Alloy/agent logs; confirm scrape target resolves |
| 401 on remote_write | Instance ID + API token; token needs `metrics:write` |
| Empty dashboard | Datasource UID matches import JSON; time range includes recent traffic |
| High cardinality | ProjectForge aggregates by route; reduce custom labels if extended |

See also [README.md](README.md) for self-hosted Prometheus + Grafana via Docker Compose.
