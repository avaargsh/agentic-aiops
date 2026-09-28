# One-command Golden Stack

This compose file is the integration owner for the three repositories. Keep them as sibling directories:

```text
workspace/
├── agentic-aiops/
├── agent-decision-lab/
└── cloud-agent-runtime/
```

Run the lightweight integration topology:

```bash
cd agentic-aiops
docker compose -f compose.golden.yml --profile demo up --build
```

The stack starts Temporal, the Cloud Agent Runtime worker, the Decision Gateway and the Golden Incident demo container.

## Decision modes

`DECISION_MODE=demo` is deterministic and lightweight. It validates service boundaries and control flow only.

`DECISION_MODE=qwen` intentionally fails closed today. The Qwen3-0.6B experiment exists in agent-decision-lab, but it is not yet promoted to the HTTP serving adapter. Do not describe demo mode as model inference.

## Target end state

```text
Alert -> Temporal Run -> Prometheus/K8s Evidence -> Decision Gateway
      -> Approval Signal -> Remediation -> Verification
      -> Run Complete + evidence://sha256/<bundle> -> Replay
```

The compose topology is not proof of a live Kubernetes remediation yet. The current checkout example uses deterministic fake read/write backends; the next milestone replaces those adapters with a disposable local Kubernetes workload and Prometheus.
