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
curl http://localhost:8000/api/v1/projects/proj_123/dashboard
curl -X POST http://localhost:8000/api/v1/projects/proj_123/compliance \
  -H "Content-Type: application/json" \
  -d '{"category":"hipaa"}'
curl http://localhost:8000/api/v1/projects/proj_123/compliance
curl http://localhost:8000/api/v1/projects/proj_123/audit-events
curl -X POST http://localhost:8000/api/v1/projects/proj_123/workflows/jobs \
  -H "Content-Type: application/json" \
  -d '{"name":"Weekly Status Automation","job_type":"weekly_status_report","schedule_type":"weekly"}'
curl http://localhost:8000/api/v1/projects/proj_123/workflows/jobs
curl -X POST http://localhost:8000/api/v1/projects/proj_123/workflows/tick
curl http://localhost:8000/api/v1/projects/proj_123/workflows/runs
curl -X POST http://localhost:8000/api/v1/projects/proj_123/reports/weekly-status
curl -X POST http://localhost:8000/api/v1/projects/proj_123/reports/weekly-status/schedule \
  -H "Content-Type: application/json" \
  -d '{"name":"Weekly Report Schedule","schedule_type":"weekly"}'
curl http://localhost:8000/api/v1/projects/proj_123/reports
curl http://localhost:8000/api/v1/projects/proj_123/graph/summary
curl http://localhost:8000/api/v1/projects/proj_123/graph/nodes
curl http://localhost:8000/api/v1/projects/proj_123/graph/edges
```

Frontend routes:

```text
/dashboard
/settings/connections
```

Automated backend verification:

```bash
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -p "test_*.py"
PYTHONPATH=backend python3 scripts/manus_autonomous_test.py
bash scripts/ci_backend_checks.sh
```

Persistence migration scaffolding (Sprint 9):

```bash
# run from repository root
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend alembic -c backend/alembic.ini downgrade -1
```
