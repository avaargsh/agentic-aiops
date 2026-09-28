#!/usr/bin/env bash
set -euo pipefail
NS=golden-demo
PROM_PORT=${PROM_PORT:-19090}
API_PORT=${API_PORT:-18001}
RUN_ID=${RUN_ID:-golden-checkout-live-001}
cleanup() { kill ${PROM_PID:-0} ${API_PID:-0} >/dev/null 2>&1 || true; }
trap cleanup EXIT

kubectl -n "$NS" port-forward svc/prometheus "$PROM_PORT":9090 >/tmp/golden-prometheus.log 2>&1 & PROM_PID=$!
kubectl proxy --port="$API_PORT" >/tmp/golden-kube-api.log 2>&1 & API_PID=$!
sleep 3
kubectl -n "$NS" scale deploy/load-generator --replicas=1
sleep 8

echo "Starting durable incident run: $RUN_ID"
echo "The process now waits at Temporal approval; Kubernetes write cannot happen before approval_resolved."
python examples/live_golden_incident.py --run-id "$RUN_ID" --prometheus "http://127.0.0.1:$PROM_PORT" --kube-api "http://127.0.0.1:$API_PORT"

kubectl -n "$NS" get deploy checkout-api
