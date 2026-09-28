#!/usr/bin/env bash
set -euo pipefail
NS=golden-demo
LOCAL_PORT=${LOCAL_PORT:-19090}
kubectl -n "$NS" port-forward svc/prometheus "$LOCAL_PORT":9090 >/tmp/golden-prometheus-port-forward.log 2>&1 &
PF_PID=$!
trap 'kill $PF_PID >/dev/null 2>&1 || true' EXIT
sleep 2
query() {
  curl -fsSG "http://127.0.0.1:${LOCAL_PORT}/api/v1/query" --data-urlencode "query=$1"
}
echo 'checkout replicas:'
kubectl -n "$NS" get deploy checkout-api -o jsonpath='{.spec.replicas}{" desired / "}{.status.readyReplicas}{" ready\n"}'
echo 'request latency gauge:'
query 'max(checkout_request_latency_seconds)'
echo
echo 'active requests:'
query 'sum(checkout_active_requests)'
echo
