# ProjectForge AI — API Reference

Base URL: `http://localhost:8000` (or `BACKEND_BASE_URL`).

## Health & storage

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health, LLM default, native Locus/OMPA status |
| GET | `/api/v1/storage/{project_id}/status` | Per-project storage backends |

## Projects & portfolio

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects` | List active projects (optional `include_archived`) |
| POST | `/api/v1/projects/register` | Create project with name, compliance, tier |
| POST | `/api/v1/projects/` | Create project and run starter ingestion/graph build |
| GET | `/api/v1/projects/{project_id}/record` | Project registry record |
| POST | `/api/v1/projects/{project_id}/archive` | Archive project |
| GET | `/api/v1/portfolio/summary` | Cross-project graph totals and summaries |

## Projects & ingestion

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/` | Create project (starter) |
| POST | `/api/v1/projects/upload` | Multipart file upload |
| POST | `/api/v1/projects/{project_id}/ingestion/database-snapshot` | PostgreSQL schema snapshot (`db_schema`, optional `connection_uri`) |

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
