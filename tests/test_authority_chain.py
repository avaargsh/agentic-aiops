from __future__ import annotations

import json

import pytest

from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.models import Incident
from agentic_aiops.operation import load_operation
from agentic_aiops.release_acceptance import build_release_evidence
from test_durable_golden_incident import Runtime
from test_golden_incident import build_runner


AUTHORITY_V1 = "sha256:" + "a" * 64
AUTHORITY_V2 = "sha256:" + "b" * 64


def _context(tmp_path, *, authority_digest=AUTHORITY_V1):
    return DurableRunContext(
        "run-authority-001",
        "session-authority-001",
        release_ref="checkout-remediator-v2",
        authority_digest=authority_digest,
        artifact_root=tmp_path,
    )


def test_incident_freezes_deployment_authority_and_exact_approval(tmp_path):
    runtime = Runtime()
    runner = build_runner()
    incident = Incident("inc-authority-001", "checkout latency", "sev2")
    ctx = _context(tmp_path)

    assert runner.run_durable(
        incident,
        runtime=runtime,
        context=ctx,
    ) is None

    run_dir = tmp_path / ctx.runtime_run_id
    bundle = json.loads((run_dir / "evidence-bundle.json").read_text())
    decision = json.loads((run_dir / "decision.json").read_text())
    attrs = decision["ledger"]["attributes"]

    assert bundle["metadata"]["authority_digest"] == AUTHORITY_V1
    assert attrs["authority_digest"] == AUTHORITY_V1
    assert attrs["evidence_digest"]
    approval_id = attrs["approval_id"]
    assert approval_id.startswith("approval-")

    runtime.state["approval_events"] = [{
        "approval_id": approval_id,
        "approved": True,
    }]
    result = runner.run_durable(
        incident,
        runtime=runtime,
        context=ctx,
    )

    assert result is not None
    operation_files = list((run_dir / "operations").glob("*.json"))
    assert len(operation_files) == 1
    operation = load_operation(run_dir, operation_files[0].stem)
    assert operation is not None
    assert operation.approval_id == approval_id
    assert operation.authority_digest == AUTHORITY_V1
    assert operation.evidence_digest == attrs["evidence_digest"]

    release_evidence = json.loads(
        (run_dir / "release-evidence.json").read_text()
    )
    assert release_evidence["operation_approval_id"] == approval_id
    assert release_evidence["authority_digest"] == AUTHORITY_V1


def test_resume_rejects_authority_drift_before_bounded_write(tmp_path):
    runtime = Runtime()
    runner = build_runner()
    incident = Incident("inc-authority-001", "checkout latency", "sev2")
    original = _context(tmp_path)

    assert runner.run_durable(
        incident,
        runtime=runtime,
        context=original,
    ) is None

    decision = json.loads(
        (
            tmp_path
            / original.runtime_run_id
            / "decision.json"
        ).read_text()
    )
    runtime.state["approval_events"] = [{
        "approval_id": decision["ledger"]["attributes"]["approval_id"],
        "approved": True,
    }]

    changed = _context(
        tmp_path,
        authority_digest=AUTHORITY_V2,
    )
    with pytest.raises(RuntimeError, match="authority_digest"):
        runner.run_durable(
            incident,
            runtime=runtime,
            context=changed,
        )

    assert not (
        tmp_path
        / original.runtime_run_id
        / "actions"
    ).exists()


def test_authority_change_changes_release_replay_digest():
    common = dict(
        release_ref="checkout-remediator-v2",
        runtime_run_id="run-authority-001",
        bundle_sha256="sha256:bundle",
        remediation_status="VERIFIED",
        post_action_ref="artifact://run-authority-001/post-action-evidence.json",
        operation_id="op-001",
        operation_phase="VERIFIED",
        operation_evidence_refs=("k8s://ready/4",),
        operation_approval_id="approval-001",
    )

    first = build_release_evidence(
        authority_digest=AUTHORITY_V1,
        **common,
    )
    second = build_release_evidence(
        authority_digest=AUTHORITY_V2,
        **common,
    )

    assert first["replay_digest"] != second["replay_digest"]
