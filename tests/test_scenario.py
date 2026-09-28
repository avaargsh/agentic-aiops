from pathlib import Path

from agentic_aiops.evaluation import (
    evaluate_aiops,
)
from agentic_aiops.scenario import (
    load_evaluation_scenario,
)


ROOT = Path(__file__).resolve().parents[1]


def test_replayable_scenario_loads_and_evaluates() -> None:
    scenario = load_evaluation_scenario(
        ROOT
        / "benchmarks/scenarios/checkout-latency.json"
    )

    result = evaluate_aiops(
        [scenario.bundle],
        [scenario.outcome],
    )

    assert scenario.case_id == "checkout-latency-001"
    assert result.unsupported_claim_rate == 0.0
    assert result.false_automation_rate == 0.0
    assert result.escalation_accuracy == 1.0
    assert result.recovery_success_rate == 1.0
