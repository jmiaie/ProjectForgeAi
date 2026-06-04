# Predictive autoscaling hooks

ProjectForge exposes autoscaling recommendations for Kubernetes HPA and external autoscalers.

## API

```
GET /api/v1/observability/autoscale
GET /api/v1/observability/capacity
```

Response includes:

- `hooks` — per-target scale up/down signals and recommended backend replica count
- `prometheus_annotations` — suggested pod annotations for GitOps wiring

## Configuration

```env
AUTOSCALE_HOOKS_ENABLED=true
AUTOSCALE_BACKEND_REPLICAS_BASE=2
AUTOSCALE_BACKEND_REPLICAS_MAX=8
```

## Kubernetes HPA example

Use capacity metrics as a custom metric source, or poll the autoscale API from a sidecar controller:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: projectforge-backend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: projectforge-backend
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
```

Pair with Prometheus adapter scraping `projectforge_http_requests_total`.

## GitOps annotation hook

Apply recommended replica hints from the API:

```bash
curl -s http://backend:8000/api/v1/observability/autoscale | jq '.prometheus_annotations'
```

See [SLO.md](../observability/SLO.md) and the capacity Grafana dashboard for correlated signals.
