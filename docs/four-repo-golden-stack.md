# Four-repo Golden Stack

This integration makes the control plane part of the executable Golden Stack instead of leaving it as a sidecar architecture document.

## Repositories

```text
workspace/
├── agent-control-plane/
├── cloud-agent-runtime/
├── agent-decision-lab/
└── agentic-aiops/
```

The `agent-control-plane` checkout must include the containerized CLI from its integration branch/merge.

## Compose path

```bash
docker compose -f compose.golden.yml --profile demo up --build
```

Before the incident demo starts, `control-plane-plan` compiles:

```text
AgentBundle checkout-sre
  -> RuntimeBinding checkout-tools
  -> RuntimeBinding checkout-workflow
  -> RuntimeBinding checkout-decision
  -> AgentRelease checkout-sre-golden-v1
```

If planning fails, Compose does not start `golden-demo`.

That creates an executable release boundary:

```text
AgentRelease
  -> resolved provider bindings
  -> Cloud Agent Runtime / Temporal
  -> Decision Gateway
  -> Golden Incident workload
```

## Current proof level

This change proves that the integration topology consumes a valid control-plane release plan before starting the demo. It does **not** yet prove that every downstream runtime event carries the release identity.

The next step for issue #16 is to propagate `AGENT_RELEASE_NAME=checkout-sre-golden-v1` into the durable Run/evidence model and assert that the same release identity reaches terminal ReleaseEvidence.

## Live target

The end state remains:

```text
real alert
 -> AgentRelease
 -> Temporal Run
 -> real Prometheus/Kubernetes evidence
 -> Decision Gateway
 -> durable approval
 -> real Kubernetes action
 -> post-action verification
 -> immutable evidence
 -> replay
```

No fake read/write adapter should be present in the final live acceptance path.
