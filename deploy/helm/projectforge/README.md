# ProjectForge AI Helm Chart

Kubernetes deployment for on-prem / enterprise installs. Mirrors `deploy/onprem/docker-compose.prod.yml`.

## Prerequisites

- Kubernetes 1.27+
- Helm 3.12+
- PersistentVolume provisioner (for Postgres, Neo4j, Temporal)
- Ingress controller (default: nginx)

## Install

```bash
helm install projectforge ./deploy/helm/projectforge \
  --namespace projectforge --create-namespace \
  -f my-values.yaml
```

## Upgrade

```bash
helm upgrade projectforge ./deploy/helm/projectforge \
  --namespace projectforge \
  -f my-values.yaml
```

## Key values

| Value | Default | Description |
|-------|---------|-------------|
| `deploymentMode` | `onprem` | Deployment mode passed to backend |
| `projectTier` | `enterprise` | Feature tier |
| `rbacEnforce` | `true` | Enable RBAC enforcement |
| `oidcEnabled` | `false` | Enable SSO/OIDC |
| `ingress.host` | `projectforge.internal` | Public hostname |
| `env.encryptionKey` | — | Replace before production |
| `postgres.password` | — | Replace before production |
| `neo4j.password` | — | Replace before production |

## OIDC

Set in values or override:

```yaml
oidcEnabled: true
oidcMock: false
env:
  oidcIssuer: https://login.example.com
  oidcClientId: projectforge
  oidcClientSecret: replace-me
```

Register redirect URI: `https://<host>/api/v1/auth/callback`

## Render locally

```bash
helm template projectforge ./deploy/helm/projectforge
```

## Compose alternative

For Docker Compose on-prem installs, see `deploy/onprem/README.md`.
