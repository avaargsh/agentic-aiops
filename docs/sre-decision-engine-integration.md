# SRE Decision Engine Integration Boundary v0.1

## Status

This document defines the integration boundary between agent-decision-lab's SRE expected-loss recommendation contract and agentic-aiops' evidence/authorization workflow. It is a design contract only: this repository does not yet call a dedicated SRE decision endpoint or consume the new sre-decision/v1 schema at runtime.

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

When runtime integration is implemented, validate the versioned response before it influences orchestration:

1. Require schema_version = sre-decision/v1 and authorized = false.
2. Bind change_id to the current proposal/run; reject cross-change or stale decisions.
3. Require every referenced evidence ID to exist in the frozen EvidenceBundle and retain the evidence digest.
4. Preserve model_id, calibration_id, policy_version, reason_code, expected_losses and excluded_actions in the Decision Ledger.
5. Treat allow/canary as recommendations only. Existing deterministic ActionPolicy, approval requirements, runtime authority and live-effect boundaries remain mandatory.
6. A hard constraint violation remains a denial/rejection path; no model score can override it.
7. After apply, evaluate post-action SLO/health evidence. A successful executor exit code alone does not prove recovery.

Do not overload the current generic /decision candidate-choice API with a second incompatible response contract. Use a dedicated typed adapter or versioned endpoint and fail closed on schema or provenance mismatch.

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
