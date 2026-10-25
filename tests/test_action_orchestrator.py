import math

import pytest

from agentic_aiops.action_orchestrator import (
    ActionOrchestrator,
    ProposedAction,
)


class FakeDecisionClient:
    def __init__(self, candidate, confidence=0.95):
        self.candidate = candidate
        self.confidence = confidence

    def decide(self, **kwargs):
        return {
            "action": "EXECUTE",
            "decision": {
                "candidate": self.candidate,
                "confidence": self.confidence,
            },
        }


class FakeApprovalSink:
    def __init__(self):
        self.requests = []

    def request(self, *, action, evidence_ids):
        self.requests.append((action, tuple(evidence_ids)))
        return "approval://1"


def test_read_action_can_execute_without_approval() -> None:
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("execute"),
    ).decide(
        ProposedAction(
            action_kind="read",
            target="metrics://checkout",
            blast_radius="single-workload",
            rollback_available=True,
            evidence_ids=("e-1",),
        )
    )

    assert result.execution_allowed is True
    assert result.approval_required is False
    assert result.ledger.outcome == "AUTHORIZED"


def test_write_action_still_requires_deterministic_approval() -> None:
    approvals = FakeApprovalSink()
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("execute"),
        approval_sink=approvals,
    ).decide(
        ProposedAction(
            action_kind="restart",
            target="deployment/checkout",
            blast_radius="single-workload",
            rollback_available=True,
            evidence_ids=("e-1", "e-2"),
        )
    )

    assert result.execution_allowed is False
    assert result.approval_required is True
    assert result.ledger.attributes["approval_ref"] == "approval://1"
    assert len(approvals.requests) == 1


def test_wide_blast_radius_cannot_auto_execute() -> None:
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("execute"),
    ).decide(
        ProposedAction(
            action_kind="restart",
            target="cluster/prod-a",
            blast_radius="cluster",
            rollback_available=True,
        )
    )

    assert result.execution_allowed is False
    assert result.approval_required is True
    assert result.policy.reason_code == "WIDE_BLAST_RADIUS"


def test_decision_plane_can_choose_human_review() -> None:
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("human_review"),
    ).decide(
        ProposedAction(
            action_kind="read",
            target="logs://checkout",
            blast_radius="single-workload",
            rollback_available=True,
        )
    )

    assert result.execution_allowed is False
    assert result.approval_required is True


def sre_recommendation(action, **overrides):
    all_losses = {
        "allow": 10.0,
        "canary": 2.0,
        "human_review": 3.0,
        "reject": 15.0,
    }
    value = {
        "schema_version": "sre-decision/v1",
        "change_id": "change-1",
        "action": action,
        "reason_code": "MINIMUM_EXPECTED_LOSS_UNDER_CONSTRAINTS",
        "expected_losses": (
            {} if action == "human_review"
            else {action: all_losses[action]}
        ),
        "excluded_actions": (
            {name: "HUMAN_REVIEW" for name in ("allow", "canary", "reject")}
            if action == "human_review"
            else {name: "NOT_SELECTED" for name in all_losses if name != action}
        ),
        "risk_context_multiplier": 1.2,
        "evidence_ids": ["e-1"],
        "model_id": "risk@sha256:abc",
        "calibration_id": "cal@sha256:def",
        "policy_version": "sre-v1",
        "authorized": False,
    }
    value.update(overrides)
    return value


def proposal_with_change():
    return ProposedAction(
        action_kind="read",
        target="metrics://checkout",
        blast_radius="single-workload",
        rollback_available=True,
        evidence_ids=("e-1",),
        change_id="change-1",
    )


def test_sre_recommendation_requires_change_identity_from_active_proposal():
    proposal = ProposedAction(
        action_kind="read",
        target="metrics://checkout",
        blast_radius="single-workload",
        rollback_available=True,
        evidence_ids=("e-1",),
    )
    with pytest.raises(ValueError, match="proposal.change_id"):
        ActionOrchestrator(
            decision_client=FakeDecisionClient("execute"),
        ).decide(
            proposal,
            change_id="change-1",
            sre_recommendation=sre_recommendation("allow"),
        )


def test_external_change_id_must_match_active_proposal_identity():
    with pytest.raises(ValueError, match="does not match proposal.change_id"):
        ActionOrchestrator(
            decision_client=FakeDecisionClient("execute"),
        ).decide(
            proposal_with_change(),
            change_id="attacker-selected-change",
            sre_recommendation=sre_recommendation(
                "allow",
                change_id="attacker-selected-change",
            ),
        )


def test_sre_reject_vetoes_model_execution():
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("execute"),
    ).decide(
        proposal_with_change(),
        change_id="change-1",
        sre_recommendation=sre_recommendation("reject"),
    )
    assert result.selected_path == "fallback"
    assert result.execution_allowed is False
    assert result.ledger.attributes["sre_action"] == "reject"
    assert result.ledger.attributes["sre_reason_code"] == "MINIMUM_EXPECTED_LOSS_UNDER_CONSTRAINTS"


def test_sre_human_review_clamps_model_execute_to_non_execution():
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("execute"),
    ).decide(
        proposal_with_change(),
        change_id="change-1",
        sre_recommendation=sre_recommendation("human_review"),
    )
    assert result.selected_path == "human_review"
    assert result.execution_allowed is False
    assert result.approval_required is True
    assert result.policy.reason_code == "SRE_REQUIRES_HUMAN_REVIEW"


def test_canary_is_not_mapped_to_full_execution_without_canary_executor():
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("execute"),
    ).decide(
        proposal_with_change(),
        change_id="change-1",
        sre_recommendation=sre_recommendation("canary"),
    )
    assert result.selected_path == "human_review"
    assert result.execution_allowed is False
    assert result.policy.reason_code == "SRE_CANARY_REQUIRES_DEDICATED_EXECUTOR"
    assert result.ledger.attributes["sre_action"] == "canary"


def test_sre_allow_does_not_upgrade_generic_fallback_to_execute():
    result = ActionOrchestrator(
        decision_client=FakeDecisionClient("fallback"),
    ).decide(
        proposal_with_change(),
        change_id="change-1",
        sre_recommendation=sre_recommendation("allow"),
    )
    assert result.selected_path == "fallback"
    assert result.execution_allowed is False


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"change_id": "other-change"}, "change_id does not match"),
        ({"evidence_ids": ["e-unrelated"]}, "not present in the active bundle"),
        ({"authorized": True}, "authorized must be false"),
    ],
)
def test_invalid_sre_recommendation_aborts_before_decision(changes, message):
    with pytest.raises(ValueError, match=message):
        ActionOrchestrator(
            decision_client=FakeDecisionClient("execute"),
        ).decide(
            proposal_with_change(),
            change_id="change-1",
            sre_recommendation=sre_recommendation("allow", **changes),
        )


@pytest.mark.parametrize(
    "confidence",
    [math.nan, math.inf, -0.01, 1.01, True, "0.95"],
)
def test_invalid_model_confidence_is_rejected_before_returning_a_decision(confidence):
    with pytest.raises(ValueError, match="confidence"):
        ActionOrchestrator(
            decision_client=FakeDecisionClient("execute", confidence=confidence),
        ).decide(
            ProposedAction(
                action_kind="read",
                target="metrics://checkout",
                blast_radius="single-workload",
                rollback_available=True,
            )
        )


def test_proposed_action_copies_evidence_ids_into_an_immutable_tuple():
    evidence_ids = ["e-1", "e-2"]
    proposal = ProposedAction(
        action_kind="read",
        target="metrics://checkout",
        blast_radius="single-workload",
        rollback_available=True,
        evidence_ids=evidence_ids,
        change_id="change-1",
    )
    evidence_ids.append("e-injected-after-construction")
    assert proposal.evidence_ids == ("e-1", "e-2")
    assert isinstance(proposal.evidence_ids, tuple)


@pytest.mark.parametrize(
    "evidence_ids",
    [
        ["e-1", "e-1"],
        ["e-1", "  "],
        "e-1",
        None,
    ],
)
def test_proposed_action_rejects_ambiguous_or_mutable_evidence_contract(evidence_ids):
    with pytest.raises(ValueError, match="evidence_ids"):
        ProposedAction(
            action_kind="read",
            target="metrics://checkout",
            blast_radius="single-workload",
            rollback_available=True,
            evidence_ids=evidence_ids,
        )


@pytest.mark.parametrize("change_id", ["", "  ", 123])
def test_proposed_action_rejects_invalid_change_identity(change_id):
    with pytest.raises(ValueError, match="change_id"):
        ProposedAction(
            action_kind="read",
            target="metrics://checkout",
            blast_radius="single-workload",
            rollback_available=True,
            change_id=change_id,
        )


def test_execute_candidate_without_confidence_fails_closed():
    class MissingConfidenceClient:
        def decide(self, **kwargs):
            return {"decision": {"candidate": "execute"}}

    result = ActionOrchestrator(
        decision_client=MissingConfidenceClient(),
    )
    with pytest.raises(ValueError, match="confidence"):
        result.decide(
            ProposedAction(
                action_kind="read",
                target="metrics://checkout",
                blast_radius="single-workload",
                rollback_available=True,
            )
        )
