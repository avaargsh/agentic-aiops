from agentic_aiops.evaluation import AIOpsEvaluation
from agentic_aiops.release_metrics import evaluation_metric_map


def test_evaluation_metric_map_matches_eval_gate_names() -> None:
    metrics = evaluation_metric_map(
        AIOpsEvaluation(
            supported_claims=10,
            unsupported_supported_claims=1,
            unsupported_claim_rate=0.1,
            automation_cases=20,
            false_automations=1,
            false_automation_rate=0.05,
            escalation_accuracy=0.9,
            unnecessary_tool_rate=0.1,
            recovery_success_rate=0.95,
        )
    )

    assert metrics == {
        "unsupported_claim_rate": 0.1,
        "false_automation_rate": 0.05,
        "escalation_accuracy": 0.9,
        "unnecessary_tool_rate": 0.1,
        "recovery_success_rate": 0.95,
    }
