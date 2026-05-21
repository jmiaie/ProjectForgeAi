# Architecture

## Overview

ProjectForgeAi is organized as a Node.js TypeScript CLI plus versioned template directories. A **forge run** loads a recipe, materializes files from templates, and writes a manifest for idempotency tracking.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   CLI       │────▶│ Recipe       │────▶│ Template engine │
│  (forge)    │     │  registry    │     │  (copy + vars)  │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                                  ▼
                                        ┌─────────────────┐
                                        │ Output directory │
                                        │ + forge.manifest │
                                        └─────────────────┘
```

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| CLI | `src/cli.ts` | Parse commands, invoke forge |
| Forge engine | `src/forge.ts` | Orchestrate run, write manifest |
| Recipes | `src/recipes/` | Map recipe name → template dir + metadata |
| Templates | `templates/<recipe>/` | Static files (and future Handlebars) |
| Tests | `src/*.test.ts` | Unit + integration smoke tests |

## Forge run lifecycle

1. **Resolve recipe** — Validate name exists; load `recipe.json` metadata.
2. **Prepare output** — Create or verify output directory (fail if non-empty unless `--force`).
3. **Materialize** — Copy template tree; apply simple `{{var}}` substitution where defined.
4. **Manifest** — Write `forge.manifest.json` with recipe id, version, timestamp, file list.

## Recipe format (v1)

```
templates/minimal/
├── recipe.json          # id, version, description
├── README.md
├── package.json
└── .github/workflows/ci.yml
```

Future: JSON Schema for specs, planner step, validation gate before materialize.

## Extension points

- **Planner** — Transform spec → template variables (not implemented v1).
- **Validator** — Lint generated tree (e.g. `npm pkg validate`) before completing run.
- **Executors** — GitHub PR creator, sandboxed shell (ADR-001 constraints).

## Security

- CLI runs only on the local machine in v1.
- Templates are repo-controlled; user-supplied template paths are rejected.
- No network calls during `forge run` for built-in recipes.

## Deployment

None for v1. Distribution via npm package (private or public TBD) and git clone.
