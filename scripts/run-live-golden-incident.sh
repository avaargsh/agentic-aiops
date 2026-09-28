#!/usr/bin/env bash
set -euo pipefail
NS=golden-demo
PROM_PORT=${PROM_PORT:-19090}
API_PORT=${API_PORT:-18001}
cleanup() { kill ${PROM_PID:-0} ${API_PID:-0} >/dev/null 2>&1 || true; }
trap cleanup EXIT

kubectl -n "$NS" port-forward svc/prometheus "$PROM_PORT":9090 >/tmp/golden-prometheus.log 2>&1 & PROM_PID=$!
kubectl proxy --port="$API_PORT" >/tmp/golden-kube-api.log 2>&1 & API_PID=$!
sleep 3

echo '1/4 inject incident'
kubectl -n "$NS" scale deploy/load-generator --replicas=1
sleep 8

echo '2/4 prove approval gate: no write allowed'
python examples/live_golden_incident.py --prometheus "http://127.0.0.1:$PROM_PORT" --kube-api "http://127.0.0.1:$API_PORT"

echo '3/4 approved remediation: agent executes scale 2 -> 4'
python examples/live_golden_incident.py --approved --prometheus "http://127.0.0.1:$PROM_PORT" --kube-api "http://127.0.0.1:$API_PORT"

echo '4/4 final state'
kubectl -n "$NS" get deploy checkout-api
