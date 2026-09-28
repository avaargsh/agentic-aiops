from __future__ import annotations

from .evaluation import AIOpsEvaluation


def evaluation_metric_map(
    result: AIOpsEvaluation,
) -> dict[str, float]:
    metrics = {
        "unsupported_claim_rate": result.unsupported_claim_rate,
        "false_automation_rate": result.false_automation_rate,
        "escalation_accuracy": result.escalation_accuracy,
        "unnecessary_tool_rate": result.unnecessary_tool_rate,
    }

    if result.recovery_success_rate is not None:
        metrics["recovery_success_rate"] = (
            result.recovery_success_rate
        )

    return metrics
