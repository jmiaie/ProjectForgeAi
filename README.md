# ProjectForge AI

Master Build Framework v14 starter scaffold.

## Quick start

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Health endpoint:

```bash
curl http://localhost:8000/health
```

Intake endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/intake/connections \
  -H "Content-Type: application/json" \
  -d '{"connector_type":"github","auth_data":{"code":"demo"},"project_id":"proj_123"}'
```

Integration wizard endpoints:

```bash
curl "http://localhost:8000/api/v1/intake/recommended?project_id=proj_123"
curl -X POST http://localhost:8000/api/v1/intake/oauth/start \
  -H "Content-Type: application/json" \
  -d '{"connector_type":"github","project_id":"proj_123","redirect_uri":"http://localhost:3000/settings/connections/callback"}'
curl -X POST http://localhost:8000/api/v1/intake/api-key \
  -H "Content-Type: application/json" \
  -d '{"connector_type":"jira","project_id":"proj_123","api_key":"replace-me"}'
curl -X POST http://localhost:8000/api/v1/intake/mcp \
  -H "Content-Type: application/json" \
  -d '{"connector_type":"mcp_server","project_id":"proj_123","server_url":"https://example-mcp-server.local"}'
curl "http://localhost:8000/api/v1/intake/connections?project_id=proj_123"
```

Workflow endpoints:

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj_123/orchestrate
curl http://localhost:8000/api/v1/projects/proj_123/workflow
curl http://localhost:8000/api/v1/projects/proj_123/graph/summary
curl http://localhost:8000/api/v1/projects/proj_123/graph/nodes
curl http://localhost:8000/api/v1/projects/proj_123/graph/edges
```
