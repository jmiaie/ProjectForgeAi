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

Workflow endpoints:

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj_123/orchestrate
curl http://localhost:8000/api/v1/projects/proj_123/workflow
```
