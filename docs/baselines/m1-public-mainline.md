# M1 public stack baseline

Verified software baseline refreshed on 2026-09-30.

The machine-readable source of truth for external repository revisions is
[`stack.lock.json`](../../stack.lock.json). This document is the human-readable
acceptance record and must not become a second dependency lock.

## Verified revisions

| Component | Verified revision | Role |
| --- | --- | --- |
| agentic-aiops PR tree | `e4fdae34e09609f83be87308ba567f2b09734c50` | Golden workload and acceptance owner |
| agentic-aiops main integration | `d25c485f68eb196b66e9023c52b989a7f292738a` | squash merge of the accepted Stack Lock change |
| agent-control-plane | `2d689b89b133dc538d1d75b14f0d2f55e496b783` | release / authority / evidence / promotion gate |
| cloud-agent-runtime | `020eb6c1c638ce17423995d340e26fcfcd242a66` | Run ↔ Workflow ↔ Sandbox lifecycle and evidence archive |
| agent-decision-lab | `1f07109b59712733dd51aab2e83618e529d9d035` | bounded Decision Gateway and benchmark contract |

The accepted PR tree and the main integration commit are recorded separately so
the acceptance evidence remains tied to the exact workflow head that GitHub
executed while the public mainline integration is also traceable.

## Acceptance evidence

[Four-repo acceptance run 36691646559](https://github.com/avaargsh/agentic-aiops/actions/runs/36691646559)
completed successfully.

The run proved:

1. `stack.lock.json` validated and resolved the three external repository SHAs;
2. Control Plane contracts, schemas and installed-wheel resources passed on
   Python 3.11 and 3.12;
3. a disposable kind cluster and Temporal-backed Golden Incident completed the
   bounded remediation path;
4. the release gate returned `PROMOTE` for the sealed positive path;
5. mutated release evidence was rejected with
   `BLOCK / INVALID_RELEASE_EVIDENCE`.

The uploaded `four-repo-acceptance-proof` artifact has digest:

```text
sha256:b00b49531fd7a79bae0716fc124cb8cbc565154e63e44c3c64de8f5917071b27
```

GitHub artifacts follow repository retention policy. The pinned revisions,
machine-readable lock and workflow allow the acceptance to be replayed after the
artifact expires.

## Baseline ownership

`stack.lock.json` owns cross-repository dependency revisions. Workflow YAML
resolves those refs from the lock and must not introduce independent hard-coded
component SHAs.

A dependency change therefore requires:

1. update the exact revision in `stack.lock.json`;
2. pass lock validation and repository unit tests;
3. pass the four-repository live acceptance;
4. preserve both the positive `PROMOTE` gate and negative
   `INVALID_RELEASE_EVIDENCE` gate;
5. refresh this human-readable record only after the proof exists.

## Scope and remaining gates

This freezes the reference software slice and its evidence contract. It does not
prove production availability, tenant-scale performance, real accelerator
performance or a trained Decision model. Decision quality measurements remain
synthetic where the benchmark uses synthetic inputs.

Temporal owns durable orchestration; Kubernetes owns sandbox execution; OPA owns
policy evaluation; object storage owns evidence retention controls; the Control
Plane remains thin.
