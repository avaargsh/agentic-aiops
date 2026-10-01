from __future__ import annotations

from dataclasses import asdict
import json
from typing import Mapping

from .action_orchestrator import OrchestratedAction
from .bundle import EvidenceBundle
from .durable_runtime import DurableRunContext
from .operation import OperationRecord
from .remediation import RemediationResult


def validate_frozen_identity(
    *,
    context: DurableRunContext,
    bundle: EvidenceBundle,
    action: OrchestratedAction,
    bundle_sha256: str,
) -> dict[str, object]:
    """Validate frozen run/release/authority identity without side effects."""

    frozen_release = bundle.metadata.get("release_ref")
    frozen_run = bundle.metadata.get("runtime_run_id")
    frozen_authority = bundle.metadata.get("authority_digest")
    ledger_attrs = dict(action.ledger.attributes)

    if context.release_ref and frozen_release != context.release_ref:
        raise RuntimeError(
            "frozen evidence release_ref does not match durable run context"
        )
    if frozen_run and frozen_run != context.runtime_run_id:
        raise RuntimeError(
            "frozen evidence runtime_run_id does not match durable run context"
        )
    if context.authority_digest and frozen_authority != context.authority_digest:
        raise RuntimeError(
            "frozen evidence authority_digest does not match durable run context"
        )
    if frozen_release and ledger_attrs.get("release_ref") != frozen_release:
        raise RuntimeError(
            "decision ledger release_ref does not match frozen evidence"
        )
    if frozen_run and ledger_attrs.get("runtime_run_id") != frozen_run:
        raise RuntimeError(
            "decision ledger runtime_run_id does not match frozen evidence"
        )
    if frozen_authority and ledger_attrs.get("authority_digest") != frozen_authority:
        raise RuntimeError(
            "decision ledger authority_digest does not match frozen evidence"
        )
    if ledger_attrs.get("evidence_digest") != bundle_sha256:
        raise RuntimeError(
            "decision ledger evidence_digest does not match frozen evidence"
        )

    return ledger_attrs


def normalize_remediation_result(
    result: RemediationResult,
) -> dict[str, object]:
    """Return the JSON-normalized form persisted inside OperationRecord.result."""

    return json.loads(json.dumps(asdict(result), sort_keys=True))


def validate_terminal_replay(
    *,
    context: DurableRunContext,
    action: OrchestratedAction,
    ledger_attrs: Mapping[str, object],
    operation: OperationRecord,
    receipt: RemediationResult,
) -> None:
    """Validate terminal operation/receipt identity without mutating runtime state."""

    if operation.phase not in {"VERIFIED", "ROLLED_BACK"}:
        raise RuntimeError(
            f"cannot replay non-terminal operation phase: {operation.phase}"
        )
    if not operation.result:
        raise RuntimeError(
            "terminal operation is missing its durable result"
        )
    if normalize_remediation_result(receipt) != operation.result:
        raise RuntimeError(
            "durable action receipt does not match terminal operation result"
        )
    if operation.runtime_run_id != context.runtime_run_id:
        raise RuntimeError(
            "operation runtime_run_id does not match durable run context"
        )
    if operation.decision_id != (action.decision_id or ""):
        raise RuntimeError(
            "operation decision_id does not match frozen decision"
        )
    if operation.evidence_digest != str(
        ledger_attrs.get("evidence_digest", "")
    ):
        raise RuntimeError(
            "operation evidence_digest does not match frozen decision"
        )

    expected_approval_id = (
        str(ledger_attrs.get("approval_id") or "")
        or None
    )
    if operation.approval_id != expected_approval_id:
        raise RuntimeError(
            "operation approval_id does not match frozen decision"
        )

    expected_authority_digest = (
        str(ledger_attrs.get("authority_digest") or "")
        or None
    )
    if operation.authority_digest != expected_authority_digest:
        raise RuntimeError(
            "operation authority_digest does not match frozen decision"
        )
