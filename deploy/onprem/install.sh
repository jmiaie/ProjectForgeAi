#!/usr/bin/env bash
# Install ProjectForge AI on Kubernetes using the on-prem Helm profile.
set -euo pipefail

RELEASE="${RELEASE:-projectforge}"
NAMESPACE="${NAMESPACE:-projectforge}"
CHART_DIR="$(cd "$(dirname "$0")/../helm/projectforge" && pwd)"

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install "${RELEASE}" "${CHART_DIR}" \
  --namespace "${NAMESPACE}" \
  -f "${CHART_DIR}/values.yaml" \
  -f "${CHART_DIR}/values-onprem.yaml" \
  "$@"

echo "Waiting for backend rollout..."
kubectl rollout status deployment/"${RELEASE}"-projectforge-backend -n "${NAMESPACE}" --timeout=300s || \
kubectl rollout status deployment/"${RELEASE}"-backend -n "${NAMESPACE}" --timeout=300s || true

echo "Install complete. Port-forward with:"
echo "  kubectl port-forward svc/${RELEASE}-projectforge-backend 8000:8000 -n ${NAMESPACE}"
