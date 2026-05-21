#!/usr/bin/env bash
# Load bundled images on an air-gapped host.
set -euo pipefail

BUNDLE="${1:?Usage: load-images.sh <bundle.tar>}"
REGISTRY="${REGISTRY:-registry.local/projectforge}"

if [[ -f "${BUNDLE}.sha256" ]]; then
  echo "Verifying checksum..."
  sha256sum -c "${BUNDLE}.sha256"
fi

echo "Loading ${BUNDLE}..."
docker load -i "${BUNDLE}"

TAG="${TAG:-0.14.0}"
echo "Tagging for local registry ${REGISTRY}..."
docker tag "projectforge-ai/backend:${TAG}" "${REGISTRY}/backend:${TAG}"
docker tag "postgres:16" "${REGISTRY}/postgres:16"
docker tag "redis:7" "${REGISTRY}/redis:7"
docker tag "neo4j:5" "${REGISTRY}/neo4j:5"

echo "Images ready. Push to your local registry or use with values-onprem.yaml:"
echo "  global.imageRegistry: ${REGISTRY}"
