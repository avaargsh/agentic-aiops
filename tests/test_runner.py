from agentic_aiops.models import (
    Hypothesis,
    Incident,
    VerificationStatus,
)
from agentic_aiops.runner import InvestigationRunner
from agentic_aiops.tools import StaticReadTool


def hypothesis_fn(investigation):
    evidence_id = next(iter(investigation.evidence))
    return [
        Hypothesis(
            hypothesis_id="h-1",
            statement="database pool saturation",
            evidence_ids=[evidence_id],
            status=VerificationStatus.SUPPORTED,
        )
    ]


def test_runner_collects_evidence_before_hypothesis() -> None:
    runner = InvestigationRunner(
        tools=[
            StaticReadTool(
                name="metrics",
                source="prometheus",
                observations=["db pool utilization 98%"],
            )
        ],
        hypothesis_fn=hypothesis_fn,
    )

    result = runner.run(
        Incident(
            incident_id="inc-1",
            summary="latency",
            severity="sev2",
        )
    )

    assert len(result.bundle.evidence) == 1
    assert len(result.supported_hypotheses) == 1
    assert result.bundle.metadata["evidence_count"] == 1
