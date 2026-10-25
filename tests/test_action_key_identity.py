from agentic_aiops.action_orchestrator import OrchestratedAction, ProposedAction
from agentic_aiops.action_receipt import action_key
from agentic_aiops.ledger import DecisionLedgerEntry
from agentic_aiops.policy import ActionDecision


def make_action(change_id=None, sre_hash=None):
    proposal = ProposedAction(
        action_kind="scale",
        target="deployment/checkout-api",
        blast_radius="single-workload",
        rollback_available=True,
        evidence_ids=("diff:sha256:abc",),
        change_id=change_id,
    )
    attributes = {"evidence_digest": "sha256:fixed-evidence"}
    if sre_hash is not None:
        attributes["sre_recommendation_sha256"] = sre_hash
    ledger = DecisionLedgerEntry(
        decision_type="remediation_escalation",
        selected_action="execute",
        policy_reason="allowed",
        evidence_ids=proposal.evidence_ids,
        attributes=attributes,
    )
    return OrchestratedAction(
        proposal=proposal,
        selected_path="execute",
        model_confidence=0.9,
        decision_id="decision-reused",
        policy=ActionDecision(True, False, "allowed"),
        execution_allowed=True,
        approval_required=False,
        ledger=ledger,
    )


def test_action_key_is_bound_to_trusted_change_identity():
    first = action_key(runtime_run_id="run-1", action=make_action("change-a"))
    second = action_key(runtime_run_id="run-1", action=make_action("change-b"))
    assert first != second


def test_action_key_is_bound_to_sre_recommendation_digest():
    first = action_key(
        runtime_run_id="run-1",
        action=make_action("change-a", "sha256:recommendation-a"),
    )
    second = action_key(
        runtime_run_id="run-1",
        action=make_action("change-a", "sha256:recommendation-b"),
    )
    assert first != second


def test_legacy_action_without_identity_keeps_historical_receipt_key():
    # Golden digest from the pre-change-id key payload. Existing durable runs
    # must still resolve their receipts after upgrading this code.
    action = make_action()
    assert action_key(runtime_run_id="run-1", action=action) == (
        "52e895e0bd43d1eeb4437afc534f2de23bdd85eae39263514a12addb328105a6"
    )
