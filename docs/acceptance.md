# Four-repo executable acceptance

The acceptance path is successful only when one canonical release/run provenance chain reaches a Control Plane `PROMOTE` decision.

```text
AgentRelease
  -> Temporal Run
  -> live Prometheus + Kubernetes evidence
  -> Decision Gateway
  -> durable approval
  -> bounded Kubernetes scale
  -> Prometheus post-action verification
  -> release-evidence.json + acceptance-metrics.json
  -> Agent Control Plane Eval/Release Gate
  -> PROMOTE
```

## Workspace

Keep these repositories as siblings:

- `agent-control-plane`
- `cloud-agent-runtime`
- `agent-decision-lab`
- `agentic-aiops`

## Contract

The runtime produces three durable acceptance artifacts under `.golden-runs/<run-id>/`:

- `post-action-evidence.json`
- `release-evidence.json`
- `acceptance-metrics.json`

The Control Plane is the final authority for promotion. A successful Kubernetes write is not sufficient. Missing or mutated evidence, failed verification, missing metrics, or a failed gate must block acceptance.

## Run

Prepare the live kind workload and Temporal/Decision services as documented by the Golden Incident guide, then:

```bash
make acceptance-build
make acceptance
```

Expected terminal lines:

```text
[5/5] PASS
release=checkout-sre-golden-v1
run_id=golden-checkout-acceptance-001
gate=PROMOTE
```

This document describes the executable contract. Do not claim a green live acceptance until the command has actually run in a compatible environment and produced its artifacts.
