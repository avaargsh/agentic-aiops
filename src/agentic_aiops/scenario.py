from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .bundle import EvidenceBundle
from .evaluation import AutomationOutcome


@dataclass(frozen=True)
class EvaluationScenario:
    case_id: str
    bundle: EvidenceBundle
    outcome: AutomationOutcome


def load_evaluation_scenario(
    path: str | Path,
) -> EvaluationScenario:
    payload = json.loads(
        Path(path).read_text(
            encoding="utf-8"
        )
    )

    case_id = str(payload["case_id"])
    outcome_data = dict(payload["outcome"])

    return EvaluationScenario(
        case_id=case_id,
        bundle=EvidenceBundle.from_dict(
            payload["bundle"]
        ),
        outcome=AutomationOutcome(
            case_id=case_id,
            automation_eligible=bool(
                outcome_data[
                    "automation_eligible"
                ]
            ),
            executed_without_approval=bool(
                outcome_data[
                    "executed_without_approval"
                ]
            ),
            expected_path=str(
                outcome_data["expected_path"]
            ),
            selected_path=str(
                outcome_data["selected_path"]
            ),
            recovery_required=bool(
                outcome_data[
                    "recovery_required"
                ]
            ),
            recovered=outcome_data.get(
                "recovered"
            ),
            tool_calls=tuple(
                outcome_data.get(
                    "tool_calls",
                    [],
                )
            ),
            required_tools=tuple(
                outcome_data.get(
                    "required_tools",
                    [],
                )
            ),
        ),
    )
