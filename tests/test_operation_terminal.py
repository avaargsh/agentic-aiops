from pathlib import Path

import pytest

from agentic_aiops.operation import OperationRecord, store_operation


def record(phase: str) -> OperationRecord:
    return OperationRecord(
        operation_id="op-terminal",
        phase=phase,
        runtime_run_id="run-001",
        decision_id="decision-001",
        action_kind="scale",
        target="deployment/checkout-api",
        evidence_digest="sha256:evidence",
        desired_state={"replicas": 4},
        evidence_refs=("evidence://terminal",),
    )


@pytest.mark.parametrize("phase", ["VERIFIED", "ROLLED_BACK", "EXECUTION_FAILED", "VERIFICATION_FAILED", "ROLLBACK_FAILED", "RECOVERY_REQUIRED"])
def test_terminal_operation_state_is_durable(tmp_path: Path, phase: str):
    store_operation(tmp_path, record(phase))
    path = tmp_path / "operations" / "op-terminal.json"
    assert path.exists()
    assert f'"phase": "{phase}"' in path.read_text()
