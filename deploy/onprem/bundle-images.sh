#!/usr/bin/env bash
# Bundle container images for air-gapped / on-prem installs.
set -euo pipefail

OUT_DIR="${1:-./deploy/onprem/bundles}"
TAG="${TAG:-0.14.0}"
mkdir -p "${OUT_DIR}"

IMAGES=(
  "projectforge-ai/backend:${TAG}"
  "postgres:16"
  "redis:7"
  "neo4j:5"
)

echo "Building backend image..."
docker build -t "projectforge-ai/backend:${TAG}" -f backend/Dockerfile .

BUNDLE="${OUT_DIR}/projectforge-images-${TAG}.tar"
echo "Saving images to ${BUNDLE}..."
docker save -o "${BUNDLE}" "${IMAGES[@]}"

sha256sum "${BUNDLE}" > "${BUNDLE}.sha256"
echo "Done. Transfer ${BUNDLE} and ${BUNDLE}.sha256 to the air-gapped host."
