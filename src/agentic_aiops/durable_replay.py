from __future__ import annotations

from dataclasses import dataclass

from .action_orchestrator import OrchestratedAction
from .action_receipt import action_key, load_receipt
from .bundle import EvidenceBundle
from .durable_runtime import DurableRunContext
from .frozen_state import load_frozen_state
from .operation import OperationRecord, load_operation
from .remediation import RemediationResult
from .replay_errors import ReplayErrorCode, ReplayValidationError
from .replay_validation import (
    validate_frozen_identity,
    validate_terminal_replay,
)


@dataclass(frozen=True)
class ReplaySnapshot:
    bundle: EvidenceBundle
    bundle_sha256: str
    action: OrchestratedAction
    remediation: RemediationResult
    operation: OperationRecord


def load_replay_snapshot(
    context: DurableRunContext,
) -> ReplaySnapshot:
    """Load and validate a terminal replay snapshot without runtime attachment."""

    frozen = load_frozen_state(context)
    if frozen is None:
        raise ReplayValidationError(
            ReplayErrorCode.FROZEN_STATE_MISSING,
            "cannot replay durable incident without frozen evidence and decision",
        )

    bundle, action = frozen
    bundle_sha256 = bundle.sha256()
    ledger_attrs = validate_frozen_identity(
        context=context,
        bundle=bundle,
        action=action,
        bundle_sha256=bundle_sha256,
    )

    key = action_key(
        runtime_run_id=context.runtime_run_id,
        action=action,
    )
    remediation = load_receipt(context.run_dir, key)
    if remediation is None:
        raise ReplayValidationError(
            ReplayErrorCode.RECEIPT_MISSING,
            "cannot replay durable incident without action receipt",
        )

    operation = load_operation(context.run_dir, key)
    if operation is None:
        raise ReplayValidationError(
            ReplayErrorCode.OPERATION_MISSING,
            "cannot replay durable incident without operation record",
        )

    validate_terminal_replay(
        context=context,
        action=action,
        ledger_attrs=ledger_attrs,
        operation=operation,
        receipt=remediation,
    )

    return ReplaySnapshot(
        bundle=bundle,
        bundle_sha256=bundle_sha256,
        action=action,
        remediation=remediation,
        operation=operation,
    )
