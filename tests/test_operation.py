from agentic_aiops.operation import OperationRecord, load_operation, store_operation, transition_operation


def test_operation_lifecycle_is_durable_and_atomic(tmp_path):
    record = OperationRecord(
        operation_id="op-001",
        phase="PREPARED",
        runtime_run_id="run-001",
        decision_id="decision-001",
        action_kind="scale",
        target="deployment/checkout-api",
        evidence_digest="sha256:evidence",
        desired_state={"replicas": 4},
    )
    store_operation(tmp_path, record)

    applied = transition_operation(
        tmp_path,
        record,
        "APPLIED",
        evidence_refs=("k8s://golden-demo/deployment/checkout-api/ready-replicas/4",),
    )
    verified = transition_operation(
        tmp_path,
        applied,
        "VERIFIED",
        evidence_refs=("prometheus://latency/0.18",),
    )

    loaded = load_operation(tmp_path, "op-001")
    assert loaded == verified
    assert loaded.phase == "VERIFIED"
    assert loaded.desired_state == {"replicas": 4}
    assert not (tmp_path / "operations" / "op-001.tmp").exists()


def test_failed_operation_retains_identity_and_error(tmp_path):
    record = OperationRecord(
        operation_id="op-002",
        phase="PREPARED",
        runtime_run_id="run-002",
        decision_id="decision-002",
        action_kind="scale",
        target="deployment/checkout-api",
        evidence_digest="sha256:evidence",
        desired_state={"replicas": 4},
    )
    store_operation(tmp_path, record)

    failed = transition_operation(
        tmp_path,
        record,
        "FAILED",
        error="TimeoutError: verification timed out",
    )

    loaded = load_operation(tmp_path, "op-002")
    assert loaded == failed
    assert loaded.runtime_run_id == "run-002"
    assert loaded.error == "TimeoutError: verification timed out"
