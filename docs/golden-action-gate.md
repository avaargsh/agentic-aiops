# Golden Action Gate

The first cross-repository runtime contract is now explicit.

```text
AgentAuthorityEnvelope
      |
      | deployment admission freezes authorityDigest
      v
AIOps Evidence
      |
      | authorityDigest participates in evidence digest
      v
ProposedAction
      |
      v
Decision Gateway
  execute / fallback / human_review
      |
      v
Deterministic ActionPolicy
      |
      +-- safe read ----------------------> authorized
      |
      +-- write / risky -----------------> RuntimeApprovalSink
                                              |
                                              v
                                     Cloud Agent Runtime
                                              |
                                       WAITING_APPROVAL
                                              |
                                       Evidence Refs
                                              |
                                         Temporal wait
```

## Important boundary

A model selecting `execute` does not mean the action executes.

For a write action:

1. the learned Decision Plane chooses a bounded path,
2. deterministic policy evaluates blast radius and rollback,
3. an approval request is created,
4. evidence IDs are converted to durable evidence references,
5. the runtime owns approval state,
6. a durable workflow can wait and resume,
7. the resulting OperationRecord freezes the exact approval ID, evidence digest and deployment authority digest,
8. release evidence carries the same authority digest back to the control plane.

An approval is therefore not a reusable permission. It authorizes one frozen action under one admitted deployment authority envelope.

## Repository coupling

`agentic-aiops` does not import `cloud-agent-runtime`.

The bridge is duck-typed against:

```python
request_approval(
    run_id,
    action=...,
    evidence_refs=...,
)
```

This keeps the runtime replaceable while preserving the safety boundary.
