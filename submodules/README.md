# Optional git submodules for upstream storage engines

ProjectForge AI ships **production-shaped local fallbacks** for Locus (BM25 RAG)
and OMPA (persistent memory) under `backend/app/storage/`. When the upstream
packages are available, set:

```bash
LOCUS_BACKEND=submodule
OMPA_BACKEND=submodule
```

## Adding upstream repositories

Replace the placeholder URLs with your fork or the canonical repos, then run:

```bash
./scripts/setup-submodules.sh
```

Or manually:

```bash
git submodule add <locus-repo-url> submodules/locus-upstream
git submodule add <ompa-repo-url> submodules/ompa-upstream
git submodule add <rtk-repo-url> submodules/rtk-upstream
git submodule update --init --recursive
```

## Installing submodule packages (editable)

When submodule repos include a `pyproject.toml`, install them into the backend venv:

```bash
cd backend
source .venv/bin/activate
pip install -e ../submodules/locus-upstream
pip install -e ../submodules/ompa-upstream
pip install -e ../submodules/rtk-upstream   # optional CLI for context compression
```

The adapters in `app.storage.locus_adapter` and `app.storage.ompa_adapter`
automatically prefer the upstream classes when `LOCUS_BACKEND=submodule` /
`OMPA_BACKEND=submodule` and the packages import successfully.

## RTK CLI

The in-repo `RTKAdapter` detects an `rtk` binary on `PATH`. Enable trimming via:

```bash
RTK_ENABLED=true
RTK_MAX_CONTEXT_CHUNKS=8
RTK_MAX_CONTEXT_CHARS=12000
```

The orchestrator applies these limits after Locus retrieval and before specialist dispatch.
