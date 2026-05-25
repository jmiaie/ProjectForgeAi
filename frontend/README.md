# ProjectForge Frontend

Next.js 15 dashboard for the ProjectForge AI v14 operator console.

## Run

```bash
npm install
npm run dev          # http://localhost:3000
npm run typecheck    # TypeScript validation
npm run build        # production build
```

Set `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`) and `NEXT_PUBLIC_DEFAULT_PROJECT_ID` in `.env.local` or docker-compose environment.

## Structure

```text
app/                  App Router pages (dashboard, settings/connections)
components/           Feature panels (see below)
lib/api.ts            Fetch wrapper for backend REST API
```

## Panels

| Component | Purpose |
|-----------|---------|
| `ProjectSummaryCards` | Runtime, graph, compliance, connection summaries |
| `IngestionPanel` | Multipart upload + manifest status |
| `GraphPanel` | Build, enrich, LLM toggle, graph actions |
| `GraphFlowViewer` | React Flow viewer; edit nodes, link DEPENDS_ON/RELATES_TO |
| `TimelinePanel` | Milestone/task dates and Gantt bars |
| `WorkbenchPanel` | Locus + graph context chat |
| `OrchestratorPanel` | Run workflow, view artifacts and history |
| `CompliancePanel` | Profile selector and audit log |
| `ConnectionsPanel` | Live connection health + IntakeWizard |
| `AutomationsPanel` | Create, approve, run, temporal status |

## API client

All backend calls go through `lib/api.ts` (`apiGet`, `apiPost`, `apiPatch`, `apiDelete`). Keep types aligned with backend response shapes in each panel.

## Styling

Global styles in `app/globals.css`. Panel layout uses shared `.panel`, `.panel-header`, `.timeline`, `.button-row` classes.
