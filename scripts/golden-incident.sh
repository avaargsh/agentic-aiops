#!/usr/bin/env bash
set -euo pipefail
ACTION=${1:-status}
NS=golden-demo
case "$ACTION" in
  inject)
    kubectl -n "$NS" scale deploy/load-generator --replicas=1
    kubectl -n "$NS" rollout status deploy/load-generator --timeout=120s
    echo 'load injected'
    ;;
  approve-scale)
    kubectl -n "$NS" scale deploy/checkout-api --replicas=4
    kubectl -n "$NS" rollout status deploy/checkout-api --timeout=180s
    echo 'checkout-api scaled 2 -> 4'
    ;;
  stop)
    kubectl -n "$NS" scale deploy/load-generator --replicas=0
    ;;
  status)
    kubectl -n "$NS" get deploy,pod,svc
    ;;
  *)
    echo "usage: $0 {inject|approve-scale|stop|status}" >&2
    exit 2
    ;;
esac
