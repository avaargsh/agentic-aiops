from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

OperationPhase = Literal[
    "PREPARED",
    "APPLIED",
    "VERIFIED",
    "ROLLED_BACK",
    "EXECUTION_FAILED",
    "VERIFICATION_FAILED",
    "ROLLBACK_FAILED",
    "RECOVERY_REQUIRED",
]

TERMINAL_OPERATION_PHASES = {
    "VERIFIED",
    "ROLLED_BACK",
    "EXECUTION_FAILED",
    "VERIFICATION_FAILED",
    "ROLLBACK_FAILED",
    "RECOVERY_REQUIRED",
}


@dataclass(frozen=True)
class OperationRecord:
    operation_id: str
    phase: OperationPhase
    runtime_run_id: str
    decision_id: str
    action_kind: str
    target: str
    evidence_digest: str
    desired_state: dict[str, object]
    approval_id: str | None = None
    authority_digest: str | None = None
    evidence_refs: tuple[str, ...] = ()
    execution: dict[str, object] | None = None
    result: dict[str, object] | None = None
    error: str | None = None
    attempt: int = 0


def operation_path(run_dir: Path, operation_id: str) -> Path:
    return run_dir / "operations" / f"{operation_id}.json"


def load_operation(run_dir: Path, operation_id: str) -> OperationRecord | None:
    path = operation_path(run_dir, operation_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["evidence_refs"] = tuple(data.get("evidence_refs", ()))
    execution = data.get("execution")
    if isinstance(execution, dict) and "evidence_ids" in execution:
        execution = dict(execution)
        execution["evidence_ids"] = tuple(execution.get("evidence_ids", ()))
        data["execution"] = execution
    return OperationRecord(**data)


def store_operation(run_dir: Path, record: OperationRecord) -> Path:
    path = operation_path(run_dir, record.operation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(record), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return path


def transition_operation(
    run_dir: Path,
    record: OperationRecord,
    phase: OperationPhase,
    *,
    evidence_refs: tuple[str, ...] | None = None,
    execution: dict[str, object] | None = None,
    result: dict[str, object] | None = None,
    error: str | None = None,
    increment_attempt: bool = False,
) -> OperationRecord:
    if record.phase in TERMINAL_OPERATION_PHASES and phase != record.phase:
        raise ValueError(
            f"terminal operation {record.operation_id} cannot transition from {record.phase} to {phase}"
        )
    updated = OperationRecord(
        operation_id=record.operation_id,
        phase=phase,
        runtime_run_id=record.runtime_run_id,
        decision_id=record.decision_id,
        action_kind=record.action_kind,
        target=record.target,
        evidence_digest=record.evidence_digest,
        desired_state=dict(record.desired_state),
        approval_id=record.approval_id,
        authority_digest=record.authority_digest,
        evidence_refs=record.evidence_refs if evidence_refs is None else evidence_refs,
        execution=record.execution if execution is None else dict(execution),
        result=record.result if result is None else dict(result),
        error=error,
        attempt=record.attempt + 1 if increment_attempt else record.attempt,
    )
    store_operation(run_dir, updated)
    return updated
