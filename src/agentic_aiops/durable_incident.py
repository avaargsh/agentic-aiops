from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Callable

from .action_orchestrator import (
    ActionOrchestrator,
    OrchestratedAction,
    ProposedAction,
)
from .action_receipt import action_key, load_receipt, store_receipt
from .bundle import EvidenceBundle
from .durable_runtime import DurableRunContext, DurableRunPort
from .frozen_state import freeze_frozen_state, load_frozen_state
from .ledger import DecisionLedgerEntry
from .models import Incident
from .operation import (
    OperationRecord,
    load_operation,
    store_operation,
    transition_operation,
)
from .release_acceptance import write_control_plane_acceptance
from .remediation import (
    ExecutionResult,
    RemediationResult,
    RollbackResult,
    SafeRemediationRunner,
    VerificationResult,
)
from .replay_validation import validate_frozen_identity
from .runner import InvestigationRunner


@dataclass(frozen=True)
class DurableIncidentOutcome:
    bundle_sha256: str
    action: OrchestratedAction
    remediation: RemediationResult
    approved: bool


def run_durable_incident(
    incident: Incident,
    *,
    runtime: DurableRunPort,
    context: DurableRunContext,
    investigation: InvestigationRunner,
    orchestrator: ActionOrchestrator,
    remediation: SafeRemediationRunner,
    proposal_fn: Callable[[EvidenceBundle], ProposedAction],
) -> DurableIncidentOutcome | None:
    run = runtime.start_or_attach(
        runtime_run_id=context.runtime_run_id,
        session_id=context.session_id,
    )

    frozen = load_frozen_state(context)
    if frozen is None:
        investigation = investigation.run(incident)
        bundle = investigation.bundle
        bundle.metadata["schema_version"] = "aiops.evidence/v1"
        if context.release_ref:
            bundle.metadata["release_ref"] = context.release_ref
            bundle.metadata["runtime_run_id"] = context.runtime_run_id
        if context.authority_digest:
            bundle.metadata["authority_digest"] = context.authority_digest
        bundle_sha256 = bundle.sha256()
        bundle.metadata["bundle_sha256"] = bundle_sha256
        proposal = proposal_fn(bundle)
        action = orchestrator.decide(
            proposal,
            evidence_digest=bundle_sha256,
        )
        if context.release_ref or context.authority_digest:
            authority_attributes = {
                **dict(action.ledger.attributes),
                "runtime_run_id": context.runtime_run_id,
            }
            if context.release_ref:
                authority_attributes["release_ref"] = context.release_ref
            if context.authority_digest:
                authority_attributes["authority_digest"] = context.authority_digest
            action = OrchestratedAction(
                proposal=action.proposal,
                selected_path=action.selected_path,
                model_confidence=action.model_confidence,
                decision_id=action.decision_id,
                policy=action.policy,
                execution_allowed=action.execution_allowed,
                approval_required=action.approval_required,
                ledger=DecisionLedgerEntry(
                    decision_type=action.ledger.decision_type,
                    selected_action=action.ledger.selected_action,
                    policy_reason=action.ledger.policy_reason,
                    evidence_ids=action.ledger.evidence_ids,
                    confidence=action.ledger.confidence,
                    requires_approval=action.ledger.requires_approval,
                    outcome=action.ledger.outcome,
                    attributes=authority_attributes,
                ),
            )
        if action.approval_required:
            approval_id = "approval-" + action_key(
                runtime_run_id=context.runtime_run_id,
                action=action,
            )[:24]
            action = OrchestratedAction(
                proposal=action.proposal,
                selected_path=action.selected_path,
                model_confidence=action.model_confidence,
                decision_id=action.decision_id,
                policy=action.policy,
                execution_allowed=action.execution_allowed,
                approval_required=action.approval_required,
                ledger=DecisionLedgerEntry(
                    decision_type=action.ledger.decision_type,
                    selected_action=action.ledger.selected_action,
                    policy_reason=action.ledger.policy_reason,
                    evidence_ids=action.ledger.evidence_ids,
                    confidence=action.ledger.confidence,
                    requires_approval=action.ledger.requires_approval,
                    outcome=action.ledger.outcome,
                    attributes={
                        **dict(action.ledger.attributes),
                        "approval_id": approval_id,
                    },
                ),
            )
        freeze_frozen_state(context, bundle, action)
    else:
        bundle, action = frozen
        bundle_sha256 = bundle.sha256()
        validate_frozen_identity(
            context=context,
            bundle=bundle,
            action=action,
            bundle_sha256=bundle_sha256,
        )

    bundle_ref = context.bundle_ref(bundle_sha256)
    state = runtime.status(run)
    approval_events = list(state.get("approval_events") or [])
    required_approval_id = (
        str(action.ledger.attributes.get("approval_id") or "")
        if action.approval_required
        else ""
    )
    approved = any(
        event.get("approved") is True
        and (
            not required_approval_id
            or event.get("approval_id") == required_approval_id
        )
        for event in approval_events
    )
    denied = any(
        event.get("approved") is False
        and (
            not required_approval_id
            or event.get("approval_id") == required_approval_id
        )
        for event in approval_events
    )

    if denied:
        return None

    if action.approval_required and not approved:
        runtime.pause(run, evidence_refs=(bundle_ref,))
        return None

    key = action_key(
        runtime_run_id=context.runtime_run_id,
        action=action,
    )
    result = load_receipt(context.run_dir, key)
    operation = load_operation(context.run_dir, key)
    if operation is None:
        operation = OperationRecord(
            operation_id=key,
            phase="PREPARED",
            runtime_run_id=context.runtime_run_id,
            decision_id=action.decision_id or "",
            action_kind=action.proposal.action_kind,
            target=action.proposal.target,
            evidence_digest=str(action.ledger.attributes.get("evidence_digest", "")),
            desired_state={"replicas": 4} if action.proposal.action_kind == "scale" else {},
            approval_id=(
                str(action.ledger.attributes.get("approval_id") or "")
                or None
            ),
            authority_digest=(
                str(action.ledger.attributes.get("authority_digest") or "")
                or None
            ),
        )
        store_operation(context.run_dir, operation)
    if result is None:
        try:
            if operation.phase in {"VERIFIED", "ROLLED_BACK"}:
                if not operation.result:
                    raise RuntimeError(
                        f"terminal operation {operation.operation_id} is missing its durable result"
                    )
                data = operation.result
                result = RemediationResult(
                    status=str(data["status"]),
                    execution=ExecutionResult(**data["execution"]) if data.get("execution") else None,
                    verification=VerificationResult(**data["verification"]) if data.get("verification") else None,
                    rollback=RollbackResult(**data["rollback"]) if data.get("rollback") else None,
                    evidence_ids=tuple(data.get("evidence_ids", ())),
                )
            elif operation.phase in {
                "EXECUTION_FAILED",
                "VERIFICATION_FAILED",
                "ROLLBACK_FAILED",
                "RECOVERY_REQUIRED",
            }:
                raise RuntimeError(
                    f"operation {operation.operation_id} is {operation.phase} and requires explicit recovery"
                )
            elif operation.phase == "APPLIED":
                if not operation.execution:
                    raise RuntimeError(
                        f"applied operation {operation.operation_id} is missing its durable execution checkpoint"
                    )
                execution_data = operation.execution
                execution = ExecutionResult(
                    changed=bool(execution_data["changed"]),
                    resource_ref=str(execution_data["resource_ref"]),
                    evidence_ids=tuple(execution_data.get("evidence_ids", ())),
                )
                result = remediation.resume_verification(action, execution)
            elif operation.phase == "PREPARED":
                def mark_applied(execution) -> None:
                    nonlocal operation
                    operation = transition_operation(
                        context.run_dir,
                        operation,
                        "APPLIED",
                        evidence_refs=tuple(execution.evidence_ids),
                        execution=asdict(execution),
                    )

                result = remediation.run(
                    action,
                    approval_granted=approved,
                    on_applied=mark_applied,
                )

            terminal_result = asdict(result)
            if result.status == "VERIFIED":
                operation = transition_operation(
                    context.run_dir,
                    operation,
                    "VERIFIED",
                    evidence_refs=result.evidence_ids,
                    result=terminal_result,
                )
            elif result.status == "ROLLED_BACK":
                operation = transition_operation(
                    context.run_dir,
                    operation,
                    "ROLLED_BACK",
                    evidence_refs=result.evidence_ids,
                    result=terminal_result,
                )
            elif result.status == "VERIFICATION_FAILED":
                operation = transition_operation(
                    context.run_dir,
                    operation,
                    "VERIFICATION_FAILED",
                    evidence_refs=result.evidence_ids,
                    result=terminal_result,
                    error=result.status,
                )
            else:
                operation = transition_operation(
                    context.run_dir,
                    operation,
                    "RECOVERY_REQUIRED",
                    evidence_refs=result.evidence_ids,
                    result=terminal_result,
                    error=result.status,
                )
            store_receipt(context.run_dir, key, result)
        except Exception as exc:
            if operation.phase == "APPLIED":
                # The side effect is durably checkpointed. A verifier/network
                # exception is not evidence that the operation failed; keep
                # APPLIED so the next attempt resumes verification without
                # executing the mutation again.
                transition_operation(
                    context.run_dir,
                    operation,
                    "APPLIED",
                    error=f"{type(exc).__name__}: {exc}",
                    increment_attempt=True,
                )
            else:
                failure_phase = (
                    "EXECUTION_FAILED"
                    if operation.phase == "PREPARED"
                    else "RECOVERY_REQUIRED"
                )
                transition_operation(
                    context.run_dir,
                    operation,
                    failure_phase,
                    error=f"{type(exc).__name__}: {exc}",
                    increment_attempt=True,
                )
            raise
    post_action = {
        "status": result.status,
        "execution_evidence_ids": list(
            result.execution.evidence_ids
            if result.execution is not None else ()
        ),
        "verification_evidence_ids": list(
            result.verification.evidence_ids
            if result.verification is not None else ()
        ),
        "verification_summary": (
            result.verification.summary
            if result.verification is not None else None
        ),
        "rollback_evidence_ids": list(
            result.rollback.evidence_ids
            if result.rollback is not None else ()
        ),
    }
    run_dir = context.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "post-action-evidence.json").write_text(
        json.dumps(post_action, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    post_action_ref = (
        f"artifact://{context.runtime_run_id}/post-action-evidence.json"
    )

    if context.release_ref:
        write_control_plane_acceptance(
            run_dir,
            release_ref=context.release_ref,
            runtime_run_id=context.runtime_run_id,
            bundle_sha256=bundle_sha256,
            remediation_status=result.status,
            post_action_ref=post_action_ref,
            operation_id=operation.operation_id,
            operation_phase=operation.phase,
            operation_evidence_refs=operation.evidence_refs,
            operation_approval_id=operation.approval_id,
            authority_digest=operation.authority_digest,
        )

    runtime.complete(
        run,
        result={
            "incident_id": incident.incident_id,
            "bundle_sha256": bundle_sha256,
            "decision": action.selected_path,
            "remediation_status": result.status,
            "release_ref": context.release_ref,
            "runtime_run_id": context.runtime_run_id,
            "authority_digest": context.authority_digest,
        },
        evidence_refs=(
            bundle_ref,
            post_action_ref,
            *result.evidence_ids,
        ),
    )

    return DurableIncidentOutcome(
        bundle_sha256=bundle_sha256,
        action=action,
        remediation=result,
        approved=approved,
    )
