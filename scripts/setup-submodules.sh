#!/usr/bin/env bash
# Initialize optional git submodules for Locus, OMPA, and RTK upstream packages.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .git ]]; then
  echo "Not a git repository; skipping submodule init."
  exit 0
fi

# Placeholder remotes — replace with real URLs before running in production.
: "${LOCUS_SUBMODULE_URL:=https://github.com/jmiaie/locus.git}"
: "${OMPA_SUBMODULE_URL:=https://github.com/jmiaie/ompa.git}"
: "${RTK_SUBMODULE_URL:=https://github.com/jmiaie/rtk.git}"

add_submodule() {
  local path="$1"
  local url="$2"
  if [[ -d "$path/.git" ]] || [[ -f "$path/.git" ]]; then
    echo "Submodule already present: $path"
    return 0
  fi
  echo "Adding submodule $path ← $url"
  git submodule add "$url" "$path" || true
}

add_submodule submodules/locus-upstream "$LOCUS_SUBMODULE_URL"
add_submodule submodules/ompa-upstream "$OMPA_SUBMODULE_URL"
add_submodule submodules/rtk-upstream "$RTK_SUBMODULE_URL"

git submodule update --init --recursive
echo "Done. Install editable packages from submodules/*/ per submodules/README.md"
