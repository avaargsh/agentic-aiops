#!/usr/bin/env bash
set -euo pipefail

RUN_ID=${RUN_ID:-golden-checkout-acceptance-001}
SESSION_ID=${SESSION_ID:-golden-demo}
RELEASE=${AGENT_RELEASE_NAME:-checkout-sre-golden-v1}
PROM=${PROMETHEUS_URL:-http://127.0.0.1:19090}
KUBE=${KUBERNETES_API:-http://127.0.0.1:18001}
DECISION=${DECISION_GATEWAY_URL:-http://127.0.0.1:8080}
RUN_DIR=".golden-runs/${RUN_ID}"
mkdir -p "$RUN_DIR"

export AGENT_RELEASE_NAME="$RELEASE"

cleanup() {
  if [[ -n "${PROM_PF_PID:-}" ]]; then kill "$PROM_PF_PID" 2>/dev/null || true; fi
  if [[ -n "${KUBE_PROXY_PID:-}" ]]; then kill "$KUBE_PROXY_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

wait_http() {
  local url="$1"
  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "endpoint not ready: $url" >&2
  return 1
}

echo "[0/5] verify live dependencies"
kubectl -n golden-demo get deploy checkout-api >/dev/null
kubectl -n golden-demo port-forward svc/prometheus 19090:9090 >"$RUN_DIR-prometheus-pf.log" 2>&1 &
PROM_PF_PID=$!
kubectl proxy --port=18001 >"$RUN_DIR-kube-proxy.log" 2>&1 &
KUBE_PROXY_PID=$!
wait_http "$PROM/-/ready"
wait_http "$KUBE/version"
wait_http "$DECISION/health" || wait_http "$DECISION/docs"

echo "[1/5] start incident and freeze pre-action evidence"
python examples/live_golden_incident.py start --run-id "$RUN_ID" --session-id "$SESSION_ID" --prometheus "$PROM" --kube-api "$KUBE" --decision "$DECISION"

APPROVAL_ID=$(python examples/live_golden_incident.py status --run-id "$RUN_ID" --session-id "$SESSION_ID" | python -c 'import json,sys; d=json.load(sys.stdin); xs=d.get("pending_approval_ids") or []; assert len(xs)==1, f"expected exactly one pending approval, got {xs}"; print(xs[0])')

echo "[2/5] approve exact durable run action: $APPROVAL_ID"
golden-approval approve --run-id "$RUN_ID" --session-id "$SESSION_ID" --approval-id "$APPROVAL_ID" --reason "four-repo acceptance"

echo "[3/5] continue bounded remediation and verify recovery"
python examples/live_golden_incident.py continue --run-id "$RUN_ID" --session-id "$SESSION_ID" --prometheus "$PROM" --kube-api "$KUBE" --decision "$DECISION"

test -f "$RUN_DIR/release-evidence.json"
test -f "$RUN_DIR/acceptance-metrics.json"
test -f "$RUN_DIR/post-action-evidence.json"

echo "[4/5] evaluate sealed runtime evidence in Agent Control Plane"
docker run --rm   -v "$PWD/demo/control-plane:/workspace:ro"   -v "$PWD/$RUN_DIR:/run:ro"   agent-control-plane:acceptance   gate /workspace/golden-eval-gate.yaml   --metrics /run/acceptance-metrics.json   --evidence /run/release-evidence.json   | tee "$RUN_DIR/release-gate.json"

grep -q '"decision": "PROMOTE"' "$RUN_DIR/release-gate.json"

echo "[5/5] PASS"
echo "release=$RELEASE"
echo "run_id=$RUN_ID"
echo "gate=PROMOTE"
