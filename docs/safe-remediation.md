# Safe Remediation Loop

The reference AIOps execution path now has a complete local safety loop.

```text
Evidence
   |
Decision Plane
   |
Deterministic Policy
   |
Approval (for writes)
   |
Execute
   |
Post-action Verification
   |
   +-- PASS ----------------> Verified
   |
   +-- FAIL
        |
        +-- rollback available --> Rollback
        |
        +-- no rollback ----------> Verification Failed
```

## Authorization

An action executes only if:

- Decision Plane selected `execute`, and
- deterministic policy allows it, and
- any required approval has been granted.

A human approval does not override a deterministic policy denial.

## Post-action verification

Execution success is not treated as incident resolution.

The verifier must generate new evidence showing whether the intended operational outcome occurred.

Examples:

- p99 latency returned under SLO,
- error rate dropped,
- pod health stabilized,
- NCCL collective recovered,
- queue depth returned to normal.

## Rollback

If post-action verification fails and the action is marked rollback-capable, the executor performs compensation and records rollback evidence.

## Evidence chain

A remediation result carries the union of:

- pre-action evidence,
- execution evidence,
- verification evidence,
- rollback evidence when applicable.

That makes the full intervention replayable and auditable without model chain-of-thought.
