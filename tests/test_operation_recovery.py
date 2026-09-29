from agentic_aiops.action_orchestrator import OrchestratedAction
from agentic_aiops.ledger import DecisionLedgerEntry
from agentic_aiops.policy import ActionDecision
from agentic_aiops.remediation import ExecutionResult, SafeRemediationRunner, VerificationResult


class NeverExecute:
    def execute(self, proposal):
        raise AssertionError("APPLIED recovery must not execute the side effect again")

    def rollback(self, proposal, execution):
        raise AssertionError("rollback not expected")


class VerifyOnly:
    def __init__(self):
        self.calls = 0

    def verify(self, proposal, execution):
        self.calls += 1
        return VerificationResult(True, ("prometheus://recovered",), "recovered")


def test_resume_verification_does_not_reexecute_side_effect():
    proposal = __import__("agentic_aiops.action_orchestrator", fromlist=["ProposedAction"]).ProposedAction(
        "scale", "deployment/checkout-api", "single-workload", True, (), "scale"
    )
    action = OrchestratedAction(
        proposal=proposal,
        selected_path="execute",
        model_confidence=1.0,
        decision_id="decision-001",
        policy=ActionDecision(True, False, "allowed"),
        execution_allowed=True,
        approval_required=False,
        ledger=DecisionLedgerEntry(
            decision_type="remediation",
            selected_action="execute",
            policy_reason="allowed",
            evidence_ids=(),
        ),
    )
    verifier = VerifyOnly()
    runner = SafeRemediationRunner(executor=NeverExecute(), verifier=verifier)
    execution = ExecutionResult(
        True,
        proposal.target,
        ("k8s://golden-demo/deployment/checkout-api/ready-replicas/4",),
    )

    result = runner.resume_verification(action, execution)

    assert result.status == "VERIFIED"
    assert verifier.calls == 1
    assert result.execution == execution
