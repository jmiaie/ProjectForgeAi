# Neo4j Kubernetes auto-healing

Automated cluster health recovery for ProjectForge Neo4j deployments.

## Backend heal endpoint

ProjectForge exposes a heal probe that re-checks all configured cluster URIs and selects a healthy write target:

```
POST /api/v1/neo4j/cluster/heal
GET  /api/v1/neo4j/cluster/status
```

Enable auto-heal logic:

```env
NEO4J_CLUSTER_FAILOVER_ENABLED=true
NEO4J_CLUSTER_AUTO_HEAL_ENABLED=true
NEO4J_CLUSTER_URIS=bolt://neo4j-core-1:7687,bolt://neo4j-core-2:7687
```

## Helm CronJob

When `neo4j.autoHeal.enabled=true` in Helm values, a CronJob calls the heal endpoint every 5 minutes:

```yaml
neo4j:
  enabled: true
  autoHeal:
    enabled: true
    schedule: "*/5 * * * *"
    image: curlimages/curl:8.11.1
```

Install or upgrade:

```bash
helm upgrade --install projectforge deploy/helm/projectforge \
  --set neo4j.autoHeal.enabled=true \
  --set env.neo4jClusterAutoHealEnabled=true
```

## Neo4j Operator (optional)

For production causal clusters, pair this heal loop with the [Neo4j Kubernetes Operator](https://neo4j.com/docs/operations-manual/current/kubernetes/):

1. Deploy Neo4j cluster via operator Helm chart
2. Point `NEO4J_URI` and `NEO4J_CLUSTER_URIS` at operator-managed Services
3. Enable ProjectForge failover + auto-heal flags
4. Import Grafana alerts from `deploy/observability/grafana/alerts/projectforge-alerts.yaml`

## Verification

```bash
curl -s http://localhost:8000/api/v1/neo4j/cluster/status | jq
curl -s -X POST http://localhost:8000/api/v1/neo4j/cluster/heal | jq
kubectl get cronjob -l app.kubernetes.io/component=neo4j-heal
```

See [RUNBOOK.md](../observability/RUNBOOK.md) for incident response when cluster status is `degraded`.
