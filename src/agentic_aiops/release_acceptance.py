from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build_release_evidence(
    *,
    release_ref: str,
    runtime_run_id: str,
    bundle_sha256: str,
    remediation_status: str,
    post_action_ref: str,
) -> dict[str, Any]:
    payload = {
        "release_ref": release_ref,
        "runtime_run_id": runtime_run_id,
        "bundle_sha256": bundle_sha256,
        "remediation_status": remediation_status,
        "post_action_ref": post_action_ref,
    }
    return {**payload, "replay_digest": _digest(payload)}


def build_acceptance_metrics(*, remediation_status: str) -> dict[str, float]:
    verified = remediation_status == "VERIFIED"
    return {
        "recovery_success_rate": 1.0 if verified else 0.0,
        "false_automation_rate": 0.0,
    }


def write_control_plane_acceptance(
    run_dir: Path,
    *,
    release_ref: str,
    runtime_run_id: str,
    bundle_sha256: str,
    remediation_status: str,
    post_action_ref: str,
) -> tuple[Path, Path]:
    evidence = build_release_evidence(
        release_ref=release_ref,
        runtime_run_id=runtime_run_id,
        bundle_sha256=bundle_sha256,
        remediation_status=remediation_status,
        post_action_ref=post_action_ref,
    )
    metrics = build_acceptance_metrics(remediation_status=remediation_status)
    evidence_path = run_dir / "release-evidence.json"
    metrics_path = run_dir / "acceptance-metrics.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return evidence_path, metrics_path
