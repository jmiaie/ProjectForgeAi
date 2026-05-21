# Contributing to ProjectForgeAi

Thank you for helping build ProjectForgeAi. This project is in early development; we prioritize clarity, safety, and reproducibility over speed.

## Getting started

1. Fork and clone the repository.
2. Install [Node.js](https://nodejs.org/) 20 or later.
3. Run `npm ci`, then `npm run build` and `npm test`.
4. Try the hello-world forge: `npm run forge -- run --recipe minimal --output ./tmp-forge-output`.

## Development workflow

- Create a branch from `main` using the pattern `cursor/<short-description>-dccd` or your own naming convention.
- Keep changes focused; one logical change per pull request.
- Update docs when behavior or architecture changes.
- Add or update tests for forge recipes and CLI behavior.

## Pull requests

- Fill out the PR template.
- Ensure CI is green.
- Prefer **PR-only** changes to generated output (see [ADR-001](docs/adr/001-execution-model.md)); do not commit secrets or real API keys.

## Reporting issues

Include:

- Recipe name and version (if applicable)
- Command you ran and full output
- Expected vs actual behavior
- Node.js version (`node -v`)

## Code of conduct

Be respectful and constructive. We are building tooling that others will trust with their repositories.
