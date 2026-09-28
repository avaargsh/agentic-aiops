import json
from pathlib import Path

from agentic_aiops.cli import main


ROOT = Path(__file__).resolve().parents[1]


def test_cli_outputs_gate_metric_map(
    monkeypatch,
    capsys,
) -> None:
    scenario = (
        ROOT
        / "benchmarks/scenarios/checkout-latency.json"
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "agentic-aiops",
            "evaluate-scenarios",
            str(scenario),
            "--metrics-only",
        ],
    )

    main()
    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload[
        "false_automation_rate"
    ] == 0.0
    assert payload[
        "unsupported_claim_rate"
    ] == 0.0
    assert payload[
        "escalation_accuracy"
    ] == 1.0
    assert payload[
        "recovery_success_rate"
    ] == 1.0
