# Agentic AIOps

Evidence-first Agentic incident investigation and safe remediation, with a runnable **Golden Incident v0.1** spanning Prometheus, Kubernetes, a Decision Gateway and Temporal durable approval.

## Golden Incident v0.1

```text
Load / Alert
    ↓
Prometheus + Kubernetes read-only investigation
    ↓
Immutable Evidence Bundle + SHA-256
    ↓
Decision Gateway (/decision)
    ↓
Deterministic Policy
    ↓
Temporal WAIT_APPROVAL
    │
    └── approval_resolved(approval_id)
              ↓
       Kubernetes scale 2 → 4
              ↓
       rollout readiness
              ↓
       Prometheus post-action verification
          ┌───┴────┐
       VERIFIED  rollback
              ↓
       Temporal COMPLETE
              ↓
         Evidence Refs / Replay
```

The key boundary is deliberate: **the model proposes; deterministic policy authorizes; Temporal owns durable lifecycle; the executor performs a bounded write; observability verifies whether the incident actually recovered.**

### Reproduce the demo

Create the disposable Kubernetes environment:

```bash
./scripts/setup-golden-kind.sh
```

Start the supporting Temporal / Decision services using `compose.golden.yml`, then run the incident entrypoint:

```bash
./scripts/run-live-golden-incident.sh
```

The start command returns control after the Run reaches durable approval. Query the frozen Decision for the exact pending approval ID:

```bash
python examples/live_golden_incident.py status \
  --run-id golden-checkout-live-001
```

Then approve that exact ID:

```bash
golden-approval approve \
  --run-id golden-checkout-live-001 \
  --approval-id <pending_approval_id> \
  --reason "scale checkout-api"
```

An approval for another action does not authorize this Run's frozen action.

Then continue the same Run:

```bash
python examples/live_golden_incident.py continue \
  --run-id golden-checkout-live-001
```

See `docs/golden-incident-v0.1.md` for the recording path and `docs/golden-stack.md` for the three-repository topology.

### What the recording should show

```text
[ALERT]         checkout-api latency above SLO
[INVESTIGATE]   Prometheus + Kubernetes read-only evidence
[EVIDENCE]      evidence://sha256/<bundle>
[DECISION]      execute / scale deployment/checkout-api
[GOVERN]        WAIT_APPROVAL (no Kubernetes write)
[APPROVAL]      exact frozen action approval_id approved
[ACTION]        replicas 2 -> 4; rollout ready
[VERIFY]        post-action latency <= SLO
[COMPLETE]      Temporal Run terminal; Evidence Refs attached
[REPLAY]        frozen bundle -> same decision; no live reads
```

This is the acceptance transcript, not a pre-recorded success claim: a real run must produce the corresponding states before the demo is described as end-to-end verified.

## Safety and correctness properties

- Evidence is collected before hypotheses and decisions.
- Investigation tools are read-only; write capability lives behind a separate executor.
- A model decision never bypasses deterministic authorization.
- Approval uses a stable action-bound `approval_id`; an unrelated approval cannot authorize the frozen action, and Temporal owns signal deduplication.
- The AIOps process does not poll while waiting for human approval.
- Successful `kubectl scale` is not treated as recovery: Prometheus must verify the post-action SLO.
- Failed verification can trigger rollback.
- Frozen Evidence Bundles support deterministic replay without querying live Prometheus/Kubernetes.

## Repository role

This repository is the **Evidence Producer + Action Orchestration** layer of the reference stack. It integrates with:

- [`agent-decision-lab`](https://github.com/avaargsh/agent-decision-lab) — synchronous Decision Plane / `/decision` boundary.
- [`cloud-agent-runtime`](https://github.com/avaargsh/cloud-agent-runtime) — Temporal-backed durable Run lifecycle and approval signals.

Together they implement:

```text
Observe → Evidence → Decide → Govern → Act → Verify → Replay
```

## Scope after v0.1

The reference slice intentionally stays narrow: Kubernetes workload degradation and bounded scale remediation. Future experiments can cover GPU/NCCL/RDMA incidents, error-budget burn and change regression without changing the control-plane boundaries demonstrated here.


## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

For cross-repository integration, the public `avaargsh/temp-runner` repository validates this project together with Agent Decision Lab and Cloud Agent Runtime on a disposable kind cluster.

## Contributing and license

Contributions are welcome through focused issues and pull requests. See `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`.

Licensed under Apache License 2.0. See `LICENSE`.
