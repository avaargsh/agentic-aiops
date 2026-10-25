from agentic_aiops.action_orchestrator import (
    ActionOrchestrator,
    ProposedAction,
)
from agentic_aiops.remediation import (
    ExecutionResult,
    RollbackResult,
    SafeRemediationRunner,
    VerificationResult,
)


class DecisionClient:
    def __init__(self, candidate="execute"):
        self.candidate = candidate

    def decide(self, **kwargs):
        return {
            "action": "EXECUTE",
            "decision": {
                "candidate": self.candidate,
                "confidence": 0.95,
            },
        }


class Executor:
    def __init__(self):
        self.executed = 0
        self.rolled_back = 0

    def execute(self, action):
        self.executed += 1
        return ExecutionResult(
            changed=True,
            resource_ref=action.target,
            evidence_ids=("e-exec",),
        )

    def rollback(self, action, execution):
        self.rolled_back += 1
        return RollbackResult(
            rolled_back=True,
            evidence_ids=("e-rollback",),
        )


class Verifier:
    def __init__(self, passed):
        self.passed = passed

    def verify(self, action, execution):
        return VerificationResult(
            passed=self.passed,
            evidence_ids=("e-verify",),
            summary="healthy" if self.passed else "still degraded",
        )


def write_action():
    return ProposedAction(
        action_kind="restart",
        target="deployment/checkout",
        blast_radius="single-workload",
        rollback_available=True,
        evidence_ids=("e-before",),
    )


def test_write_action_requires_approval_before_execution() -> None:
    orchestrated = ActionOrchestrator(
        decision_client=DecisionClient(),
    ).decide(write_action())

    executor = Executor()
    result = SafeRemediationRunner(
        executor=executor,
        verifier=Verifier(True),
    ).run(
        orchestrated,
        approval_granted=False,
    )

    assert result.status == "NOT_AUTHORIZED"
    assert executor.executed == 0


def test_approved_write_executes_and_verifies() -> None:
    orchestrated = ActionOrchestrator(
        decision_client=DecisionClient(),
    ).decide(write_action())

    executor = Executor()
    result = SafeRemediationRunner(
        executor=executor,
        verifier=Verifier(True),
    ).run(
        orchestrated,
        approval_granted=True,
    )

    assert result.status == "VERIFIED"
    assert executor.executed == 1
    assert executor.rolled_back == 0
    assert result.evidence_ids == (
        "e-before",
        "e-exec",
        "e-verify",
    )


def test_failed_post_action_verification_rolls_back() -> None:
    orchestrated = ActionOrchestrator(
        decision_client=DecisionClient(),
    ).decide(write_action())

    executor = Executor()
    result = SafeRemediationRunner(
        executor=executor,
        verifier=Verifier(False),
    ).run(
        orchestrated,
        approval_granted=True,
    )

    assert result.status == "ROLLED_BACK"
    assert executor.executed == 1
    assert executor.rolled_back == 1
    assert "e-rollback" in result.evidence_ids


def test_fallback_path_never_executes() -> None:
    orchestrated = ActionOrchestrator(
        decision_client=DecisionClient("fallback"),
    ).decide(write_action())

    executor = Executor()
    result = SafeRemediationRunner(
        executor=executor,
        verifier=Verifier(True),
    ).run(
        orchestrated,
        approval_granted=True,
    )

    assert result.status == "NOT_SELECTED_FOR_EXECUTION"
    assert executor.executed == 0


def sre_recommendation(action):
    losses = {
        "allow": 10.0,
        "canary": 2.0,
        "human_review": 3.0,
        "reject": 15.0,
    }
    return {
        "schema_version": "sre-decision/v1",
        "change_id": "change-1",
        "action": action,
        "reason_code": "MINIMUM_EXPECTED_LOSS_UNDER_CONSTRAINTS",
        "expected_losses": {} if action == "human_review" else {action: losses[action]},
        "excluded_actions": (
            {name: "HUMAN_REVIEW" for name in ("allow", "canary", "reject")}
            if action == "human_review"
            else {name: "NOT_SELECTED" for name in losses if name != action}
        ),
        "risk_context_multiplier": 1.2,
        "evidence_ids": ["e-before"],
        "model_id": "risk@sha256:abc",
        "calibration_id": "cal@sha256:def",
        "policy_version": "sre-v1",
        "authorized": False,
    }


def test_sre_canary_cannot_execute_as_full_remediation_even_if_approval_flag_is_true():
    orchestrated = ActionOrchestrator(
        decision_client=DecisionClient(),
    ).decide(
        write_action(),
        change_id="change-1",
        sre_recommendation=sre_recommendation("canary"),
    )
    executor = Executor()
    result = SafeRemediationRunner(
        executor=executor,
        verifier=Verifier(True),
    ).run(
        orchestrated,
        approval_granted=True,
    )
    assert orchestrated.policy.reason_code == "SRE_CANARY_REQUIRES_DEDICATED_EXECUTOR"
    assert result.status == "NOT_SELECTED_FOR_EXECUTION"
    assert executor.executed == 0
    assert executor.rolled_back == 0


def test_sre_reject_never_executes_remediation():
    orchestrated = ActionOrchestrator(
        decision_client=DecisionClient(),
    ).decide(
        write_action(),
        change_id="change-1",
        sre_recommendation=sre_recommendation("reject"),
    )
    executor = Executor()
    result = SafeRemediationRunner(
        executor=executor,
        verifier=Verifier(True),
    ).run(
        orchestrated,
        approval_granted=True,
    )
    assert orchestrated.policy.reason_code == "SRE_REJECT_RECOMMENDATION"
    assert result.status == "NOT_SELECTED_FOR_EXECUTION"
    assert executor.executed == 0
