from agentic_aiops.alertmanager import incident_from_alertmanager
from agentic_aiops.models import Hypothesis, VerificationStatus
from agentic_aiops.report import render_rca_markdown
from agentic_aiops.runner import InvestigationRunner
from agentic_aiops.tools import StaticReadTool


incident = incident_from_alertmanager(
    {
        "groupKey": "checkout-latency",
        "status": "firing",
        "commonLabels": {
            "severity": "sev2",
            "cluster": "prod-a",
            "namespace": "checkout",
            "service": "checkout-api",
        },
        "commonAnnotations": {
            "summary": "checkout p99 latency increased",
        },
    }
)


def propose(investigation):
    evidence_id = next(iter(investigation.evidence))
    return [
        Hypothesis(
            hypothesis_id="db-pool",
            statement="database connection pool saturation",
            evidence_ids=[evidence_id],
            status=VerificationStatus.SUPPORTED,
        )
    ]


runner = InvestigationRunner(
    tools=[
        StaticReadTool(
            name="prometheus",
            source="prometheus",
            observations=[
                "checkout CPU normal; downstream DB pool utilization 98%"
            ],
        ),
        StaticReadTool(
            name="kubernetes",
            source="kubernetes",
            observations=[
                "checkout pods healthy; no restart spike"
            ],
        ),
    ],
    hypothesis_fn=propose,
)

result = runner.run(incident)
print(render_rca_markdown(result.bundle))
