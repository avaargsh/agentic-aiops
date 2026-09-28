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
