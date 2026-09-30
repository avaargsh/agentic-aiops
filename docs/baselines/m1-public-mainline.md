# M1 public mainline baseline

Frozen software baseline verified on 2026-09-30. All four repositories are public
and carry Apache-2.0 license metadata. Each checkout is pinned to a full commit SHA.

| Repository | Verified revision |
| --- | --- |
| agentic-aiops | `438ed9f3ccbffaef2466c064e32306e4324f831b` |
| agent-control-plane | `7d19efaca02bfcae248d49847fe52a6b45f775d4` |
| cloud-agent-runtime | `06f90a019bde4d7a7434f051d23aaa43e62d6377` |
| agent-decision-lab | `07bc6324868304d3f847e4d91b2c4e4691b4c0a5` |

## Acceptance evidence

[Exact-head main push acceptance](https://github.com/avaargsh/agentic-aiops/actions/runs/36685817087)
passed with Python 3.11 / 3.12 Control Plane contract jobs and a fresh live kind +
Temporal acceptance job. Control Plane reports 151 passed, 1 skipped per matrix
environment; isolated wheel installation and packaged-schema validation also pass.

The live run records all four checked-out revisions in
`four-repo-revisions.json`, completes the bounded incident/approval workflow,
and obtains `PROMOTE` from the Control Plane release gate. Mutating release
evidence while retaining the positive path's authority digest obtains
`BLOCK` with `INVALID_RELEASE_EVIDENCE`. This prevents an authority mismatch
from masquerading as proof of evidence validation.

The run's `four-repo-acceptance-proof` artifact has digest
`sha256:d9575ecff88976f48f71f8445346ef344786ace995f92455f801a0ebe6e33077`.
[Captured release-gate outputs](m1-public-mainline-proof.json) preserve the actual positive and mutated-evidence JSON results in git.

GitHub artifacts follow the repository retention policy; the immutable revisions
and workflow allow replay after artifact expiry.

[Exact-head unit](https://github.com/avaargsh/agentic-aiops/actions/runs/36685817010)
and [test](https://github.com/avaargsh/agentic-aiops/actions/runs/36685817000)
push workflows also passed.

## Scope and remaining gates

This freezes the reference software slice and its evidence contract. It does not
prove production availability, tenant-scale performance, real accelerator
performance or a trained Decision model. Decision metrics remain synthetic where
the benchmark uses synthetic inputs. Temporal owns durable orchestration; the
Control Plane remains thin.

Subsequent changes must record new exact revisions and repeat the main push live
acceptance before replacing this baseline. Concurrent AgentOS work is integrated
by pinning verified revisions, without rewriting its history.
