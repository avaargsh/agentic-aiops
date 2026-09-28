import os

from agentic_aiops.kubernetes_tool import KubernetesListTool
from agentic_aiops.models import (
    Hypothesis,
    Incident,
    VerificationStatus,
)
from agentic_aiops.prometheus_tool import (
    PrometheusQuery,
    PrometheusReadTool,
)
from agentic_aiops.runner import InvestigationRunner


prometheus = PrometheusReadTool(
    base_url=os.environ[
        "PROMETHEUS_URL"
    ],
    queries=[
        PrometheusQuery(
            name="checkout_http_5xx",
            promql=(
                'sum(rate(http_requests_total{'
                'service="checkout",status=~"5.."}[5m]))'
            ),
        )
    ],
)

kubernetes = KubernetesListTool(
    api_server=os.environ[
        "KUBERNETES_API_SERVER"
    ],
    resource_path_template=(
        "/api/v1/namespaces/{namespace}/pods"
    ),
)


def propose(investigation):
    evidence_ids = list(
        investigation.evidence
    )
    return [
        Hypothesis(
            hypothesis_id="needs-analysis",
            statement=(
                "Live evidence was collected; "
                "root cause still requires verification."
            ),
            evidence_ids=evidence_ids,
            status=VerificationStatus.UNVERIFIED,
        )
    ]


runner = InvestigationRunner(
    tools=[prometheus, kubernetes],
    hypothesis_fn=propose,
)

result = runner.run(
    Incident(
        incident_id="live-demo",
        summary="checkout degradation",
        severity="sev2",
        scope="namespace=checkout",
    )
)

print(result.bundle.to_dict())
