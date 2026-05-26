# ProjectForge AI — API Reference

Base URL: `http://localhost:8000` (or `BACKEND_BASE_URL`).

## Health & storage

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health, LLM default, native Locus/OMPA status |
| GET | `/api/v1/deploy/status` | Deployment mode, hardening flags, build bundle info |
| GET | `/api/v1/observability/status` | Metrics/tracing configuration |
| GET | `/api/v1/observability/metrics` | Request counts, latency, recent traces |
| GET | `/api/v1/observability/prometheus` | Prometheus text exposition format |
| GET | `/api/v1/observability/traces/jaeger` | Jaeger-compatible trace batch export |
| GET | `/api/v1/observability/traces/otlp` | OTLP JSON trace payload |
| GET | `/api/v1/observability/slo` | Live SLO snapshot and error-budget status |
| GET | `/api/v1/neo4j/cluster/status` | Neo4j cluster member health and active write URI |
| POST | `/api/v1/neo4j/cluster/heal` | Re-check cluster members and select healthy write URI |
| GET | `/api/v1/storage/{project_id}/status` | Per-project storage backends |

## Regions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/regions` | Available regions and data residency zones |
| GET | `/api/v1/tenants/{tenant_id}/region` | Tenant region assignment; validates `X-ProjectForge-Region` when routing enabled |

## Tenants (SaaS)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tenants` | List registered tenants |
| POST | `/api/v1/tenants/register` | Create tenant workspace (optional `region`) |
| GET | `/api/v1/tenants/{tenant_id}/status` | Tenant isolation status and roots |

Pass `X-ProjectForge-Tenant` on requests when tenant isolation is enabled.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tenants/{tenant_id}/billing/usage` | Tenant usage summary |
| GET | `/api/v1/tenants/{tenant_id}/billing/quota` | Quota limits and remaining capacity |
| GET | `/api/v1/tenants/{tenant_id}/billing/check?action=` | Check quota for action (`project_create`, `llm_call`, etc.) |
| POST | `/api/v1/tenants/{tenant_id}/billing/checkout` | Create Stripe/mock checkout session (`billing_mode`: `payment` or `subscription`) |
| POST | `/api/v1/tenants/{tenant_id}/billing/subscribe` | Create recurring subscription checkout |
| GET | `/api/v1/tenants/{tenant_id}/billing/subscription` | Tenant subscription status |
| POST | `/api/v1/tenants/{tenant_id}/billing/portal` | Stripe customer portal session |
| POST | `/api/v1/tenants/{tenant_id}/billing/subscription/cancel` | Cancel subscription (`at_period_end` optional) |
| GET | `/api/v1/tenants/{tenant_id}/billing/overage` | LLM token overage summary and estimated charges |
| POST | `/api/v1/tenants/{tenant_id}/billing/usage/report` | Report LLM overage to Stripe metered billing |
| GET | `/api/v1/tenants/{tenant_id}/billing/invoices` | List tenant invoices |
| GET | `/api/v1/billing/status` | Billing provider configuration status |
| POST | `/api/v1/billing/webhook` | Stripe webhook (`checkout.session.completed`, `invoice.paid`, subscription events) |
| GET | `/api/v1/tenants/{tenant_id}/status` | Includes Neo4j tenant database routing and read-replica metadata |

## Projects & portfolio

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects` | List active projects (optional `include_archived`) |
| POST | `/api/v1/projects/register` | Create project with name, compliance, tier |
| POST | `/api/v1/projects/` | Create project and run starter ingestion/graph build |
| GET | `/api/v1/projects/{project_id}/record` | Project registry record |
| POST | `/api/v1/projects/{project_id}/archive` | Archive project |
| GET | `/api/v1/portfolio/summary` | Cross-project graph totals and summaries |
| GET | `/api/v1/portfolio/compliance/rollup` | Cross-project compliance posture rollup |
| GET | `/api/v1/portfolio/risk/rollup` | Cross-project Risk node rollup by severity |
| GET | `/api/v1/portfolio/intelligence/dashboard` | Executive dashboard widgets |
| POST | `/api/v1/portfolio/orchestrator/run` | Portfolio-level risk/compliance orchestrator run |
| GET | `/api/v1/portfolio/orchestrator/runs` | Portfolio orchestrator run history |
| GET | `/api/v1/portfolio/orchestrator/runs/{portfolio_run_id}` | Portfolio orchestrator run detail |

## Projects & ingestion

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/` | Create project (starter) |
| POST | `/api/v1/projects/upload` | Multipart file upload |
| POST | `/api/v1/projects/{project_id}/ingestion/database-snapshot` | PostgreSQL schema snapshot (`db_schema`, optional `connection_uri`) |

## LLM routing & billing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{project_id}/llm/routing` | Model routing preview by tier and task type |
| GET | `/api/v1/projects/{project_id}/llm/keys` | List configured BYO provider keys |
| POST | `/api/v1/projects/{project_id}/llm/keys` | Save encrypted BYO key (`provider`, `api_key`) |
| DELETE | `/api/v1/projects/{project_id}/llm/keys/{provider}` | Remove BYO key |
| GET | `/api/v1/projects/{project_id}/llm/usage` | Per-project LLM call and token usage summary |

## Spatial / RTK

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{project_id}/spatial/assets` | List geo-tagged assets |
| POST | `/api/v1/projects/{project_id}/spatial/assets` | Register spatial asset |
| POST | `/api/v1/projects/{project_id}/spatial/sync-graph` | Index graph nodes with lat/lon properties |
| GET | `/api/v1/projects/{project_id}/spatial/map` | Map bounds and markers |
| GET | `/api/v1/projects/{project_id}/spatial/status` | RTK adapter status |

Supported upload types include PDF, email, mbox, Office, images, **IFC**, **DWG**, and **codebase archives** (zip/tar).

## Graph

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{project_id}/graph/build` | Build graph from ingestion manifest |
| POST | `/api/v1/projects/{project_id}/graph/enrich` | LLM/heuristic enrichment |
| GET | `/api/v1/projects/{project_id}/graph` | Full graph snapshot |
| GET | `/api/v1/projects/{project_id}/graph/status` | Graph backend status |
| POST | `/api/v1/graph/bootstrap` | Apply Neo4j schema migrations |
| POST | `/api/v1/projects/{project_id}/graph/nodes` | Create node |
| PATCH | `/api/v1/projects/{project_id}/graph/nodes/{node_id}` | Update node properties |
| DELETE | `/api/v1/projects/{project_id}/graph/nodes/{node_id}` | Delete node |
| POST | `/api/v1/projects/{project_id}/graph/edges` | Create edge |
| DELETE | `/api/v1/projects/{project_id}/graph/edges` | Delete edge |

## Workbench

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{project_id}/workbench/query` | Locus + graph context query |

## Orchestrator

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/orchestrator/run` | Run specialist workflow (`resume`, `requested_agents` optional) |
| GET | `/api/v1/projects/{project_id}/orchestrator/status` | Latest or specific run status |
| GET | `/api/v1/projects/{project_id}/orchestrator/runs` | Run history (includes `branch_path`) |
| GET | `/api/v1/projects/{project_id}/orchestrator/audit` | Orchestrator audit events |
| GET | `/api/v1/projects/{project_id}/access/members` | List project members (requires `access.manage`) |
| POST | `/api/v1/projects/{project_id}/access/members` | Assign member role |
| GET | `/api/v1/projects/{project_id}/access/check?action=` | Check permission for actor |
| GET | `/api/v1/projects/{project_id}/upgrade/status` | Feature tier status |
| POST | `/api/v1/projects/{project_id}/upgrade/self-improve` | Compliance-gated self-improvement run |

## Compliance

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{project_id}/compliance/profile` | Current profile |
| POST | `/api/v1/projects/{project_id}/compliance/profile` | Set profile category |
| GET | `/api/v1/projects/{project_id}/compliance/audit` | Audit event stream |
| GET | `/api/v1/projects/{project_id}/compliance/export/soc2` | SOC 2 control mapping export (requires `compliance.export`) |

## Auth / SSO

Prefix: `/api/v1/auth`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | OIDC configuration and active session count |
| GET | `/login` | Start OIDC flow (returns authorization URL) |
| GET | `/callback` | OIDC authorization callback |
| POST | `/mock-login` | Development mock SSO (when `OIDC_MOCK=true`) |
| GET | `/me` | Current session (Bearer token) |
| POST | `/logout` | Revoke session token |

## Integrations (Intake)

Prefix: `/api/v1/intake`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/connections/recommended` | Recommended connectors by compliance |
| POST | `/connections/oauth/start` | Start OAuth PKCE flow |
| GET | `/oauth/{connector_type}/callback` | OAuth callback |
| POST | `/connections` | Connect via API key or token payload |
| GET | `/connections/{project_id}` | List connections |
| GET | `/connections/{project_id}/{connector_type}/status` | Connection status |
| GET | `/connections/{project_id}/{connector_type}/health` | Live health check |
| GET | `/connections/{project_id}/mcp/tools` | MCP tool discovery |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| POST | `/connections/webhook/register` | Register outbound webhook (`webhook_url`, `events`, optional `send_test`) |
| POST | `/connections/{project_id}/webhook/test` | Send test event to registered webhook |

## Automations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{project_id}/automations` | Create automation |
| GET | `/api/v1/projects/{project_id}/automations` | List automations |
| POST | `/api/v1/projects/{project_id}/automations/{id}/run` | Run now |
| POST | `/api/v1/projects/{project_id}/automations/{id}/approve` | Approve gated run |
| POST | `/api/v1/projects/{project_id}/automations/{id}/retry` | Retry failed run |
| GET | `/api/v1/projects/{project_id}/automations/runs` | Run history |
| GET | `/api/v1/projects/{project_id}/automations/dead-letters` | Dead-letter queue |
| GET | `/api/v1/automations/temporal/status` | Temporal worker status |
| POST | `/api/v1/automations/temporal/run-due` | Evaluate due schedules |
| POST | `/api/v1/automations/temporal/start-due` | Start due workflows via Temporal |
