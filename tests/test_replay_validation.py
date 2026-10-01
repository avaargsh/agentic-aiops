from dataclasses import replace

import pytest

from agentic_aiops.action_orchestrator import (
    OrchestratedAction,
    ProposedAction,
)
from agentic_aiops.bundle import EvidenceBundle
from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.ledger import DecisionLedgerEntry
from agentic_aiops.models import Incident
from agentic_aiops.operation import OperationRecord
from agentic_aiops.policy import ActionDecision
from agentic_aiops.remediation import RemediationResult
from agentic_aiops.replay_errors import ReplayErrorCode, ReplayValidationError
from agentic_aiops.replay_validation import (
    normalize_remediation_result,
    validate_frozen_identity,
    validate_terminal_replay,
)


RUN_ID = "run-1"
RELEASE_REF = "release://checkout-v1"
AUTHORITY_DIGEST = "sha256:authority"
DECISION_ID = "decision-1"
APPROVAL_ID = "approval-1"


def fixture():
    context = DurableRunContext(
        RUN_ID,
        "session-1",
        release_ref=RELEASE_REF,
        authority_digest=AUTHORITY_DIGEST,
    )
    bundle = EvidenceBundle(
        incident=Incident("inc-1", "checkout latency", "sev2"),
        metadata={
            "release_ref": RELEASE_REF,
            "runtime_run_id": RUN_ID,
            "authority_digest": AUTHORITY_DIGEST,
        },
    )
    bundle_sha256 = bundle.sha256()
    action = OrchestratedAction(
        proposal=ProposedAction(
            "scale",
            "deployment/checkout-api",
            "single-workload",
            True,
        ),
        selected_path="execute",
        model_confidence=0.99,
        decision_id=DECISION_ID,
        policy=ActionDecision(True, True, "APPROVAL_REQUIRED"),
        execution_allowed=False,
        approval_required=True,
        ledger=DecisionLedgerEntry(
            decision_type="remediation_escalation",
            selected_action="execute",
            policy_reason="APPROVAL_REQUIRED",
            requires_approval=True,
            outcome="APPROVAL_REQUIRED",
            attributes={
                "release_ref": RELEASE_REF,
                "runtime_run_id": RUN_ID,
                "authority_digest": AUTHORITY_DIGEST,
                "evidence_digest": bundle_sha256,
                "approval_id": APPROVAL_ID,
            },
        ),
    )
    return context, bundle, action, bundle_sha256


def with_ledger(action, **updates):
    attrs = {**dict(action.ledger.attributes), **updates}
    return replace(
        action,
        ledger=replace(action.ledger, attributes=attrs),
    )


@pytest.mark.parametrize(
    ("mutation", "code", "message"),
    [
        ("context-release", ReplayErrorCode.RELEASE_MISMATCH, "frozen evidence release_ref"),
        ("context-run", ReplayErrorCode.RUN_MISMATCH, "frozen evidence runtime_run_id"),
        ("context-authority", ReplayErrorCode.AUTHORITY_MISMATCH, "frozen evidence authority_digest"),
        ("ledger-release", ReplayErrorCode.RELEASE_MISMATCH, "decision ledger release_ref"),
        ("ledger-run", ReplayErrorCode.RUN_MISMATCH, "decision ledger runtime_run_id"),
        ("ledger-authority", ReplayErrorCode.AUTHORITY_MISMATCH, "decision ledger authority_digest"),
        ("ledger-evidence", ReplayErrorCode.EVIDENCE_MISMATCH, "decision ledger evidence_digest"),
    ],
)
def test_validate_frozen_identity_rejects_each_identity_drift(
    mutation,
    code,
    message,
):
    context, bundle, action, bundle_sha256 = fixture()

    if mutation == "context-release":
        context = replace(context, release_ref="release://other")
    elif mutation == "context-run":
        bundle.metadata["runtime_run_id"] = "run-other"
        bundle_sha256 = bundle.sha256()
        action = with_ledger(
            action,
            runtime_run_id="run-other",
            evidence_digest=bundle_sha256,
        )
    elif mutation == "context-authority":
        context = replace(context, authority_digest="sha256:other")
    elif mutation == "ledger-release":
        action = with_ledger(action, release_ref="release://other")
    elif mutation == "ledger-run":
        action = with_ledger(action, runtime_run_id="run-other")
    elif mutation == "ledger-authority":
        action = with_ledger(action, authority_digest="sha256:other")
    elif mutation == "ledger-evidence":
        action = with_ledger(action, evidence_digest="sha256:other")

    with pytest.raises(ReplayValidationError, match=message) as exc:
        validate_frozen_identity(
            context=context,
            bundle=bundle,
            action=action,
            bundle_sha256=bundle_sha256,
        )
    assert exc.value.code is code


def terminal_fixture():
    context, bundle, action, bundle_sha256 = fixture()
    ledger_attrs = validate_frozen_identity(
        context=context,
        bundle=bundle,
        action=action,
        bundle_sha256=bundle_sha256,
    )
    receipt = RemediationResult(
        status="VERIFIED",
        execution=None,
        verification=None,
        rollback=None,
        evidence_ids=("evidence-1",),
    )
    operation = OperationRecord(
        operation_id="operation-1",
        phase="VERIFIED",
        runtime_run_id=RUN_ID,
        decision_id=DECISION_ID,
        action_kind="scale",
        target="deployment/checkout-api",
        evidence_digest=bundle_sha256,
        desired_state={"replicas": 4},
        approval_id=APPROVAL_ID,
        authority_digest=AUTHORITY_DIGEST,
        result=normalize_remediation_result(receipt),
    )
    return context, action, ledger_attrs, receipt, operation


@pytest.mark.parametrize(
    ("mutation", "code", "message"),
    [
        ("phase", ReplayErrorCode.OPERATION_NOT_TERMINAL, "cannot replay non-terminal operation phase"),
        ("missing-result", ReplayErrorCode.RESULT_MISSING, "terminal operation is missing"),
        ("receipt", ReplayErrorCode.RECEIPT_MISMATCH, "durable action receipt does not match"),
        ("run", ReplayErrorCode.RUN_MISMATCH, "operation runtime_run_id"),
        ("decision", ReplayErrorCode.DECISION_MISMATCH, "operation decision_id"),
        ("evidence", ReplayErrorCode.EVIDENCE_MISMATCH, "operation evidence_digest"),
        ("approval", ReplayErrorCode.APPROVAL_MISMATCH, "operation approval_id"),
        ("authority", ReplayErrorCode.AUTHORITY_MISMATCH, "operation authority_digest"),
    ],
)
def test_validate_terminal_replay_rejects_each_invariant_drift(
    mutation,
    code,
    message,
):
    context, action, ledger_attrs, receipt, operation = terminal_fixture()

    if mutation == "phase":
        operation = replace(operation, phase="PREPARED")
    elif mutation == "missing-result":
        operation = replace(operation, result=None)
    elif mutation == "receipt":
        operation = replace(operation, result={"status": "ROLLED_BACK"})
    elif mutation == "run":
        operation = replace(operation, runtime_run_id="run-other")
    elif mutation == "decision":
        operation = replace(operation, decision_id="decision-other")
    elif mutation == "evidence":
        operation = replace(operation, evidence_digest="sha256:other")
    elif mutation == "approval":
        operation = replace(operation, approval_id="approval-other")
    elif mutation == "authority":
        operation = replace(operation, authority_digest="sha256:other")

    with pytest.raises(ReplayValidationError, match=message) as exc:
        validate_terminal_replay(
            context=context,
            action=action,
            ledger_attrs=ledger_attrs,
            operation=operation,
            receipt=receipt,
        )
    assert exc.value.code is code


def test_replay_validators_accept_consistent_snapshot():
    context, bundle, action, bundle_sha256 = fixture()
    ledger_attrs = validate_frozen_identity(
        context=context,
        bundle=bundle,
        action=action,
        bundle_sha256=bundle_sha256,
    )
    context, action, _, receipt, operation = terminal_fixture()

    validate_terminal_replay(
        context=context,
        action=action,
        ledger_attrs=ledger_attrs,
        operation=operation,
        receipt=receipt,
    )
