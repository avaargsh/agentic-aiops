#!/usr/bin/env bash
set -euo pipefail
CLUSTER=${CLUSTER:-golden-aiops}
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --name "$CLUSTER"
kubectl apply -f demo/k8s/golden-stack.yaml
kubectl -n golden-demo rollout status deploy/checkout-api --timeout=180s
kubectl -n golden-demo rollout status deploy/prometheus --timeout=180s
echo 'Golden demo cluster ready.'
echo 'Start incident: scripts/golden-incident.sh inject'
