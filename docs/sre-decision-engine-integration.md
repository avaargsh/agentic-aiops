# SRE Decision Engine Integration Boundary v0.1

## Status

This document defines the integration boundary between agent-decision-lab's SRE expected-loss recommendation contract and agentic-aiops' evidence/authorization workflow.

The optional `sre_recommendation` argument to `ActionOrchestrator.decide()` now invokes `validate_sre_recommendation()`. The validator checks schema version, binds the recommendation to the trusted `ProposedAction.change_id`, requires any redundant external `change_id` argument to match that proposal field, verifies referenced evidence IDs against the proposal evidence list, validates typed expected losses/exclusion coverage, and enforces `authorized=false`. The recommendation is applied as a **veto-only overlay**: rejection short-circuits execution, human review stays non-executable, canary is routed to human review because no dedicated canary executor exists, and allow never upgrades a generic model fallback.

This is a tested library boundary, not yet an authenticated service boundary. There is no dedicated HTTP endpoint, signed recommendation provenance, freshness/assessment digest, mandatory enforcement for every write, or live control-plane integration. Until these are implemented, the caller must be trusted to supply the intended recommendation; this optional payload must not be treated as proof that a specific risk assessment was issued by a trusted service.

## Ownership

- **agent-decision-lab** owns risk assessment contracts, calibrated probability provenance, expected-loss comparison and the advisory recommendation.
- **agentic-aiops** owns incident evidence collection, hypothesis validation, remediation orchestration, durable approval, post-action verification and replayable outcome records.
- **agent-control-plane** remains the authoritative boundary for action authorization, durable execution identity, lifecycle and policy enforcement.

Do not duplicate expected-loss math inside agentic-aiops. Do not reinterpret a recommendation as an authorization grant.

## Input mapping

The SRE risk assessment should bind to the current change and evidence bundle and include:

- stable change ID and changed-resource scope;
- calibrated change-failure probability, model identity and calibration artifact identity;
- impact cost in an organization-defined unit;
- current error-budget remaining ratio and active-incident state;
- rollback availability and blast-radius class;
- input-completeness and uncertainty signals;
- evidence IDs, plus deterministic hard-constraint violations.

Error-budget and incident context must be captured at the decision timestamp, with source and timestamp provenance. Stale or missing critical values must route to human review, not be imputed as healthy.

## Recommendation consumption

Current library behavior:

1. Require exact `sre-decision/v1` fields and `authorized = false`.
2. Require the caller to provide the expected `change_id`; reject a mismatch.
3. Require non-empty recommendation evidence IDs, all of which must exist in the current proposal evidence IDs.
4. Retain the complete normalized recommendation plus its SHA-256 in the Decision Ledger.
5. An SRE `reject` never selects execution. `human_review` is non-executable. `canary` is downgraded to human review until a canary-specific executor is available. `allow` does not override a generic model fallback.
6. Existing deterministic ActionPolicy, approval requirements, runtime authority and live-effect boundaries remain in force.
7. Post-action verification and rollback remain the execution runner's responsibility.

Remaining gaps: no freshness/assessment digest or cryptographic authenticity check exists yet, and the recommendation is an optional caller-supplied input rather than a mandatory SRE service result. Do not use this optional path as a production enforcement boundary until recommendation provenance and run/evidence freshness are authenticated. Do not overload the current generic `/decision` candidate-choice API; a future remote SRE service should use a dedicated typed adapter or versioned endpoint.

## Evaluation protocol

Compare the same frozen, time-ordered change/incident cases across:

- deterministic rules only;
- rules plus a baseline table model;
- rules plus calibrated probability and expected-loss selection;
- optional semantic model signals in shadow mode.

Report severe-incident recall, precision at fixed review capacity, Brier score/ECE, false-automation rate, expected loss, abstention/review rate, review effort, change-failure rate, error-budget consumption, rollback success and recovery time. Split by time and by incident/change lineage to avoid near-duplicate leakage. Synthetic scenarios prove interface behavior only, not production predictive quality.

## Rollout gates

1. Shadow mode: record recommendations, do not alter action execution.
2. Human-reviewed mode: compare advice to an independently recorded human decision and subsequent outcome.
3. Bounded automation: enable only for low-impact, reversible actions inside the approved blast-radius and error-budget bounds.
4. Any schema drift, missing evidence, stale calibration, high uncertainty, active incident, or exhausted error budget removes automated actions from the feasible set.
5. Reinforcement learning stays offline until the action set, expected-loss costs, replay corpus and independent safety gates are frozen.
