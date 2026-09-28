import pytest

from agentic_aiops.bundle import EvidenceBundle
from agentic_aiops.evaluation import (
    AutomationOutcome,
    evaluate_aiops,
)
from agentic_aiops.models import (
    Evidence,
    Hypothesis,
    Incident,
    VerificationStatus,
)


def bundle_with_claims() -> EvidenceBundle:
    return EvidenceBundle(
        incident=Incident(
            "inc-1",
            "checkout latency",
            "sev2",
        ),
        evidence=[
            Evidence(
                "e-1",
                "prometheus",
                "db pool 98%",
            )
        ],
        hypotheses=[
            Hypothesis(
                "h-good",
                "db saturation",
                ["e-1"],
                VerificationStatus.SUPPORTED,
            ),
            Hypothesis(
                "h-bad",
                "network failure",
                ["missing-evidence"],
                VerificationStatus.SUPPORTED,
            ),
        ],
    )


def test_aiops_evaluation_metrics() -> None:
    result = evaluate_aiops(
        [bundle_with_claims()],
        [
            AutomationOutcome(
                case_id="safe-read",
                automation_eligible=True,
                executed_without_approval=True,
                expected_path="execute",
                selected_path="execute",
                recovery_required=False,
                tool_calls=("metrics",),
                required_tools=("metrics",),
            ),
            AutomationOutcome(
                case_id="unsafe-write",
                automation_eligible=False,
                executed_without_approval=True,
                expected_path="human_review",
                selected_path="execute",
                recovery_required=True,
                recovered=False,
                tool_calls=("metrics", "logs", "kubernetes"),
                required_tools=("metrics", "logs"),
            ),
        ],
    )

    assert result.supported_claims == 2
    assert result.unsupported_supported_claims == 1
    assert result.unsupported_claim_rate == pytest.approx(0.5)
    assert result.false_automations == 1
    assert result.false_automation_rate == pytest.approx(0.5)
    assert result.escalation_accuracy == pytest.approx(0.5)
    assert result.unnecessary_tool_rate == pytest.approx(0.25)
    assert result.recovery_success_rate == pytest.approx(0.0)


def test_no_supported_claims_is_zero_rate() -> None:
    result = evaluate_aiops(
        [],
        [],
    )

    assert result.unsupported_claim_rate == 0.0
    assert result.false_automation_rate == 0.0
    assert result.recovery_success_rate is None
