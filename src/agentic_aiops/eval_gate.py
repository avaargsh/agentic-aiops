from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EvalGateResult:
    passed: bool
    reason: str
    release_ref: str | None
    runtime_run_id: str | None


def evaluate_golden_release(
    *,
    release_ref: str | None,
    runtime_run_id: str | None,
    remediation_status: str,
    provenance_valid: bool,
    post_action: Mapping[str, object],
) -> EvalGateResult:
    """Minimal release gate for the Golden Incident acceptance path."""
    if not release_ref or not runtime_run_id:
        return EvalGateResult(False, "missing canonical release/run identity", release_ref, runtime_run_id)
    if not provenance_valid:
        return EvalGateResult(False, "release/run/evidence provenance invalid", release_ref, runtime_run_id)
    if remediation_status != "VERIFIED":
        return EvalGateResult(False, f"remediation not verified: {remediation_status}", release_ref, runtime_run_id)
    if post_action.get("status") != "VERIFIED":
        return EvalGateResult(False, "post-action evidence is not VERIFIED", release_ref, runtime_run_id)
    verification = list(post_action.get("verification_evidence_ids") or [])
    if not verification:
        return EvalGateResult(False, "missing post-action verification evidence", release_ref, runtime_run_id)
    return EvalGateResult(True, "golden incident acceptance criteria satisfied", release_ref, runtime_run_id)
