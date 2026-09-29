from agentic_aiops.release_acceptance import build_release_evidence


def test_release_evidence_binds_terminal_operation():
    evidence = build_release_evidence(
        release_ref="release/golden-v1",
        runtime_run_id="run-001",
        bundle_sha256="sha256:bundle",
        remediation_status="VERIFIED",
        post_action_ref="artifact://run-001/post-action-evidence.json",
        operation_id="op-001",
        operation_phase="VERIFIED",
        operation_evidence_refs=("k8s://ready/4", "prometheus://latency/0.18"),
    )

    assert evidence["operation_id"] == "op-001"
    assert evidence["operation_phase"] == "VERIFIED"
    assert evidence["operation_evidence_refs"] == [
        "k8s://ready/4",
        "prometheus://latency/0.18",
    ]
    assert evidence["replay_digest"].startswith("sha256:")


def test_operation_identity_changes_release_replay_digest():
    common = dict(
        release_ref="release/golden-v1",
        runtime_run_id="run-001",
        bundle_sha256="sha256:bundle",
        remediation_status="VERIFIED",
        post_action_ref="artifact://run-001/post-action-evidence.json",
        operation_phase="VERIFIED",
        operation_evidence_refs=("k8s://ready/4",),
    )
    first = build_release_evidence(operation_id="op-001", **common)
    second = build_release_evidence(operation_id="op-002", **common)

    assert first["replay_digest"] != second["replay_digest"]
