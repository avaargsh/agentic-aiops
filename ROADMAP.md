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
- [ ] Temporal investigation workflow
- [x] approval sink contract
- [x] Cloud Agent Runtime approval bridge
- [x] evidence-backed approval refs
- [ ] bounded retries
- [x] approval-gated write execution
- [x] post-action verification
- [x] rollback on failed verification
- [x] end-to-end remediation evidence chain

## v0.4 — Evaluation and Decision Plane
- [x] Decision Gateway HTTP client
- [x] bounded escalation path
- [x] learned decision + deterministic policy separation
- [x] Golden Action Gate example
- [ ] incident scenario corpus
- [ ] unsupported-claim metric
- [ ] false automation metric
- [ ] evidence precision / coverage
- [ ] MTTD / MTTR simulation
