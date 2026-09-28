# Agentic AIOps

An evidence-first reference architecture for **Agentic incident investigation and safe remediation**.

This project focuses on the transition from traditional alert correlation and runbook automation to an Agent system that can gather evidence, form hypotheses, verify them and propose or execute bounded actions.

## Core loop

```text
Signal / Alert
  |
Event Normalization
  |
Context + Topology
  |
Investigation Planner
  |
Read-only Tools
  |
Evidence Graph
  |
Hypothesis / RCA
  |
Verification
  |
Decision Gate
  |----------------------|
  |                      |
Advisory              Approved Action
                         |
                    Safe Executor
                         |
                  Post-action Verify
                         |
                       Replay
```

## Design principles

- Evidence before explanation.
- Read-only investigation before write actions.
- Model reasoning never replaces deterministic authorization.
- Every conclusion should link to observable evidence.
- Every remediation needs blast-radius, approval and rollback semantics.
- Evaluation must test false automation, not only RCA accuracy.

## Initial integrations

- Alertmanager / Prometheus
- Kubernetes
- OpenTelemetry
- logs and traces
- CMDB / topology source
- MCP tool adapters
- policy / approval service
- Temporal for durable workflows

## Initial scenarios

- Kubernetes workload degradation
- GPU / NCCL / RDMA performance incidents
- API latency / error-budget burn
- capacity saturation
- configuration/change regression

## Status

Private incubation repository. v0.1 will implement one end-to-end incident slice with replayable evidence.
