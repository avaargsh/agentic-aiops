from agentic_aiops.action_orchestrator import OrchestratedAction, ProposedAction
from agentic_aiops.bundle import EvidenceBundle
from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.frozen_state import freeze_frozen_state, load_frozen_state
from agentic_aiops.ledger import DecisionLedgerEntry
from agentic_aiops.models import Incident
from agentic_aiops.policy import ActionDecision


def test_frozen_state_preserves_trusted_change_identity_and_evidence(tmp_path):
    context = DurableRunContext(
        runtime_run_id="run-change-identity",
        session_id="session-1",
        artifact_root=tmp_path,
    )
    bundle = EvidenceBundle(
        incident=Incident("inc-1", "checkout latency", "sev2"),
    )
    proposal = ProposedAction(
        action_kind="scale",
        target="deployment/checkout-api",
        blast_radius="single-workload",
        rollback_available=True,
        evidence_ids=["diff:sha256:abc", "slo:snapshot:123"],
        change_id="change-123",
    )
    action = OrchestratedAction(
        proposal=proposal,
        selected_path="human_review",
        model_confidence=None,
        decision_id=None,
        policy=ActionDecision(False, True, "SRE_REQUIRES_HUMAN_REVIEW"),
        execution_allowed=False,
        approval_required=True,
        ledger=DecisionLedgerEntry(
            decision_type="remediation_escalation",
            selected_action="human_review",
            policy_reason="SRE_REQUIRES_HUMAN_REVIEW",
            evidence_ids=proposal.evidence_ids,
            requires_approval=True,
            outcome="APPROVAL_REQUIRED",
            attributes={
                "change_id": "change-123",
                "sre_action": "human_review",
            },
        ),
    )

    freeze_frozen_state(context, bundle, action)
    restored = load_frozen_state(context)
    assert restored is not None
    _, restored_action = restored

    assert restored_action.proposal.change_id == "change-123"
    assert restored_action.proposal.evidence_ids == (
        "diff:sha256:abc",
        "slo:snapshot:123",
    )
    assert restored_action.ledger.attributes["change_id"] == "change-123"
    assert restored_action.ledger.attributes["sre_action"] == "human_review"
