# Decision Plane and Runtime Integration

Agentic AIOps treats learned decisions and execution authorization as separate layers.

```text
Evidence
   |
Proposed Action
   |
Decision Gateway
   |   execute / fallback / human_review
   v
Deterministic ActionPolicy
   |
   +-- read-only + allowed ----------> Execute
   |
   +-- write / wider risk ----------> ApprovalSink
   |
   +-- disallowed ------------------> Block / Review
```

## Decision Plane

The Decision Gateway can make bounded choices such as:

- execute,
- fallback to System-2 reasoning,
- require human review.

It does not grant authorization.

## Deterministic policy

The local reference policy currently enforces:

- read-only actions may execute without approval,
- narrow write actions require approval when rollback exists,
- wide blast radius requires review,
- write actions without rollback cannot auto-execute.

This is intentionally conservative.

## ApprovalSink

The AIOps repository depends on an abstract `ApprovalSink`, not on a concrete runtime package.

A Cloud Agent Runtime adapter can map:

```text
ApprovalSink.request(...)
        |
        v
Run -> WAITING_APPROVAL
        |
        v
Temporal durable wait
        |
operator decision
        |
        v
approval_resolved signal
```

This keeps AIOps, Decision Plane and Runtime independently replaceable.

## Decision Ledger

The resulting ledger records externally meaningful facts:

- selected bounded path,
- confidence,
- deterministic policy reason,
- evidence IDs,
- whether approval is required,
- target / blast radius,
- approval reference when created.

Hidden model reasoning is not used as the audit source.
