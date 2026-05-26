# ProjectForge observability stack

Prometheus + Grafana templates for scraping ProjectForge AI metrics.

## Metrics endpoint

ProjectForge exposes Prometheus text format at:

```
GET /api/v1/observability/prometheus
```

Enable with:

```env
OTEL_EXPORTER_ENABLED=true
OBSERVABILITY_ENABLED=true
METRICS_ENABLED=true
```

## Prometheus scrape config

Use `prometheus-scrape.yml` as a scrape config fragment:

```yaml
scrape_configs:
  - job_name: projectforge
    metrics_path: /api/v1/observability/prometheus
    static_configs:
      - targets: ['backend:8000']
```

For Kubernetes, annotate the backend Service or add a ServiceMonitor.

## Grafana dashboard

Import `grafana/dashboards/projectforge-overview.json`:

1. Open Grafana → Dashboards → Import
2. Upload the JSON file or paste contents
3. Select your Prometheus datasource

Panels include:

- HTTP request rate
- Average latency
- Top routes
- 5xx error count

## Docker Compose overlay (optional)

Add to your compose stack:

```yaml
  prometheus:
    image: prom/prometheus:v2.54.0
    volumes:
      - ./deploy/observability/prometheus-scrape.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:11.2.0
    ports:
      - "3001:3000"
    volumes:
      - ./deploy/observability/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

## Jaeger traces

Export recent traces for debugging:

```
GET /api/v1/observability/traces/jaeger
```

Wire Jaeger collector to ingest OTLP/JSON batches in production.
