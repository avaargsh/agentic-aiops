# Roadmap

## v0.1 — Evidence model
- [x] Incident / Evidence / Hypothesis
- [x] explicit verification state
- [x] deterministic action gate
- [x] topology entity model
- [x] change-event model
- [x] Decision Ledger record

## v0.2 — One incident slice
- [x] Alertmanager input
- [x] read-tool interface
- [x] Prometheus/Kubernetes-style read-tool fixtures
- [x] replayable evidence bundle
- [x] investigation runner
- [x] explicit hypothesis verification state
- [x] RCA markdown report
- [x] replay into Investigation
- [x] live Prometheus read-only adapter
- [x] live Kubernetes read-only adapter
- [x] bearer-token / CA-aware JSON HTTP client

## v0.3 — Durable workflow and remediation
- [x] Temporal investigation workflow
- [x] approval sink contract
- [x] Cloud Agent Runtime approval bridge
- [x] evidence-backed approval refs
- [x] bounded retries / desired-state reconciliation for the Golden Kubernetes action
- [x] approval-gated write execution
- [x] post-action verification
- [x] rollback on failed verification
- [x] end-to-end remediation evidence chain

## v0.4 — Evaluation and Decision Plane
- [x] Decision Gateway HTTP client
- [x] bounded escalation path
- [x] learned decision + deterministic policy separation
- [x] Golden Action Gate example
- [x] replayable scenario contract
- [x] first synthetic incident regression scenario
- [x] unsupported supported-claim metric
- [x] false automation metric
- [x] escalation accuracy
- [x] unnecessary tool rate
- [x] recovery success rate
- [ ] evidence precision / coverage
- [ ] MTTD / MTTR simulation


## v0.5 — SRE Decision Engine Integration
- [ ] add a dedicated typed adapter for sre-decision/v1; do not overload the candidate-choice API
- [ ] bind recommendation change ID, evidence IDs and digest to the active proposal/run
- [ ] propagate timestamped SLO/error-budget and active-incident context
- [ ] retain risk/model/calibration/policy provenance in the decision ledger
- [ ] prove that recommendations cannot bypass ActionPolicy, approval or control-plane authority
- [ ] replay time-split change/incident cases and compare expected loss with rules-only baseline
- [ ] run shadow mode before enabling any bounded automated action
