# ProjectForgeAi — Vision & Scope

## Problem

Turning a product or technical spec into a working repository is repetitive. Teams redo scaffolding for every greenfield project. AI assistants help ad hoc, but output is inconsistent and hard to audit.

## Vision

**ProjectForgeAi Forge CLI** produces reproducible, reviewable repository scaffolding from versioned **forge recipes** and JSON specs—alongside the v14 **Project Management OS** (backend + frontend in this repo).

## Forge v0.2 (current)

- `forge validate --spec <file>` — JSON Schema validation
- `forge run --spec <file>` — planner maps spec → recipe + template vars
- Recipes: `minimal`, `express-api`
- `forge.manifest.json` on every run
- ADR-001: local output, non-destructive defaults

## Platform (v14 scaffold)

See root [README.md](../README.md) for FastAPI backend, Next.js intake wizard, docker-compose, and sprint branches (LangGraph, persistence, OAuth, project graph, etc.).

## Out of scope (forge)

- Auto GitHub PR creation
- LLM spec interpretation (schema-first for now)
- Hosted forge API

## Principles

1. **Reproducibility** — Recipes versioned; specs validated before forge.
2. **Review before merge** — Local output or manual PR.
3. **Least privilege** — No secrets in templates.
4. **Test the forge** — CI smoke for each recipe.
