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
        "EXECUTION_FAILED",
        error="TimeoutError: execution failed",
    )

    loaded = load_operation(tmp_path, "op-002")
    assert loaded == failed
    assert loaded.runtime_run_id == "run-002"
    assert loaded.error == "TimeoutError: execution failed"


def test_terminal_result_survives_without_action_receipt(tmp_path):
    result = {
        "status": "VERIFIED",
        "execution": {
            "changed": True,
            "resource_ref": "deployment/checkout-api",
            "evidence_ids": ["k8s://ready/4"],
        },
        "verification": {
            "passed": True,
            "evidence_ids": ["prometheus://latency/0.18"],
            "summary": "ok",
        },
        "rollback": None,
        "evidence_ids": ["k8s://ready/4", "prometheus://latency/0.18"],
    }
    record = OperationRecord(
        operation_id="op-terminal-result",
        phase="VERIFIED",
        runtime_run_id="run-001",
        decision_id="decision-001",
        action_kind="scale",
        target="deployment/checkout-api",
        evidence_digest="sha256:evidence",
        desired_state={"replicas": 4},
        result=result,
    )
    store_operation(tmp_path, record)

    loaded = load_operation(tmp_path, record.operation_id)
    assert loaded is not None
    assert loaded.phase == "VERIFIED"
    assert loaded.result == result


def test_applied_operation_persists_changed_false_execution_checkpoint(tmp_path):
    record = OperationRecord(
        operation_id="op-reconciled",
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
        evidence_refs=("k8s://desired-replicas/4",),
        execution={
            "changed": False,
            "resource_ref": "deployment/checkout-api",
            "evidence_ids": ("k8s://desired-replicas/4",),
        },
    )

    recovered = load_operation(tmp_path, applied.operation_id)
    assert recovered is not None
    assert recovered.execution is not None
    assert recovered.execution["changed"] is False
    assert recovered.execution["resource_ref"] == "deployment/checkout-api"


def test_applied_retry_keeps_phase_and_records_attempt(tmp_path):
    record = OperationRecord(
        operation_id="op-retry",
        phase="APPLIED",
        runtime_run_id="run-001",
        decision_id="decision-001",
        action_kind="scale",
        target="deployment/checkout-api",
        evidence_digest="sha256:evidence",
        desired_state={"replicas": 4},
        execution={
            "changed": True,
            "resource_ref": "deployment/checkout-api",
            "evidence_ids": ("k8s://desired-replicas/4",),
        },
    )
    store_operation(tmp_path, record)

    retriable = transition_operation(
        tmp_path,
        record,
        "APPLIED",
        error="TimeoutError: prometheus unavailable",
        increment_attempt=True,
    )

    recovered = load_operation(tmp_path, retriable.operation_id)
    assert recovered is not None
    assert recovered.phase == "APPLIED"
    assert recovered.attempt == 1
    assert recovered.error == "TimeoutError: prometheus unavailable"
    assert recovered.execution == record.execution


def test_terminal_operation_cannot_transition_to_another_phase(tmp_path):
    record = OperationRecord(
        operation_id="op-terminal",
        phase="VERIFIED",
        runtime_run_id="run-001",
        decision_id="decision-001",
        action_kind="scale",
        target="deployment/checkout-api",
        evidence_digest="sha256:evidence",
        desired_state={"replicas": 4},
    )
    store_operation(tmp_path, record)

    import pytest
    with pytest.raises(ValueError, match="terminal operation"):
        transition_operation(tmp_path, record, "RECOVERY_REQUIRED")

    assert load_operation(tmp_path, record.operation_id) == record
