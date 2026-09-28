# Golden Incident Demo v0.1

The first vertical slice joins the existing three planes without introducing another agent framework:

```text
Prometheus + Kubernetes
        |
        v
EvidenceBundle (immutable SHA-256)
        |
        v
Decision Gateway
        |
        v
Approval Gate / Temporal Run
        |
        v
Remediation
        |
        v
Post-action Verification
        |
        v
Evidence / Replay
```

## Contract

`GoldenIncidentRunner` is deliberately orchestration-only. Investigation remains read-only, learned routing stays in the Decision Gateway, authorization stays deterministic, and write execution remains behind approval policy.

The evidence bundle is content-addressed with `sha256()`. The embedded `bundle_sha256` metadata field is excluded from hashing so persisted bundles can verify themselves without a circular digest.

## Safety invariant

A write action that requires approval returns `NOT_AUTHORIZED` until the caller supplies an approved resolution. The durable runtime/Temporal layer owns waiting and signal deduplication; this module does not bypass that lifecycle.

## Replay

Replay reconstructs investigation state from the frozen Evidence Bundle. It does not query Prometheus or Kubernetes again. This gives model/provider comparisons the same incident input and makes decision changes auditable.

## v0.1 demo target

`checkout-api`: high CPU + p95 latency -> evidence collection -> SCALE_OUT proposal -> approval -> replicas 2 to 4 -> metric verification -> replay.
