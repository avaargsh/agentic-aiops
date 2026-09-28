"""Runnable checkout-api Golden Incident demo using deterministic fake backends.

Swap the fake HTTP clients for real Prometheus/Kubernetes endpoints to exercise live reads.
Write execution remains simulated; production mutation belongs behind the runtime approval path.
"""

import json
from dataclasses import dataclass

from agentic_aiops.action_orchestrator import ActionOrchestrator, ProposedAction
from agentic_aiops.golden_incident import GoldenIncidentRunner
from agentic_aiops.kubernetes_tool import KubernetesListTool
from agentic_aiops.models import Hypothesis, Incident, VerificationStatus
from agentic_aiops.prometheus_tool import PrometheusQuery, PrometheusReadTool
from agentic_aiops.remediation import ExecutionResult, RollbackResult, SafeRemediationRunner, VerificationResult
from agentic_aiops.runner import InvestigationRunner

class FakePrometheusClient:
    def get_json(self, url):
        return {"status": "success", "data": {"resultType": "vector", "result": [{"metric": {"service": "checkout-api"}, "value": [1, "0.91"]}]}}

class FakeKubernetesClient:
    def get_json(self, url):
        return {"metadata": {"resourceVersion": "42"}, "items": [{"metadata": {"name": "checkout-api-7c9"}}, {"metadata": {"name": "checkout-api-8fd"}}]}

class DemoDecisionGateway:
    def decide(self, **kwargs):
        return {"decision": {"candidate": "execute", "confidence": 0.93}}

@dataclass
class DemoExecutor:
    replicas: int = 2
    def execute(self, action):
        self.replicas = 4
        return ExecutionResult(True, action.target, ("e-scale-2-to-4",))
    def rollback(self, action, execution):
        self.replicas = 2
        return RollbackResult(True, ("e-rollback-to-2",))

class DemoVerifier:
    def verify(self, action, execution):
        return VerificationResult(True, ("e-p95-recovered",), "p95 returned below SLO threshold")

def hypotheses(investigation):
    return [Hypothesis("h-capacity", "checkout-api is capacity constrained", list(investigation.evidence), VerificationStatus.SUPPORTED)]

prometheus = PrometheusReadTool(base_url="https://prometheus.demo", queries=[PrometheusQuery("checkout_cpu", 'avg(rate(container_cpu_usage_seconds_total{pod=~"checkout-api.*"}[5m]))')], client=FakePrometheusClient())
kubernetes = KubernetesListTool(api_server="https://kubernetes.demo", resource_path_template="/api/v1/namespaces/{namespace}/pods", client=FakeKubernetesClient())
executor = DemoExecutor()
runner = GoldenIncidentRunner(investigation=InvestigationRunner(tools=[prometheus, kubernetes], hypothesis_fn=hypotheses), orchestrator=ActionOrchestrator(decision_client=DemoDecisionGateway()), remediation=SafeRemediationRunner(executor=executor, verifier=DemoVerifier()), proposal_fn=lambda bundle: ProposedAction("scale", "deployment/checkout-api", "single-workload", True, tuple(item.evidence_id for item in bundle.evidence), "scale checkout-api from 2 to 4 replicas"))
incident = Incident("inc-checkout-001", "checkout-api p95 latency above SLO", "sev2", "namespace=checkout")

pending = runner.run(incident)
print(json.dumps(pending.to_dict(), indent=2, default=str))
assert pending.remediation.status == "NOT_AUTHORIZED"
assert executor.replicas == 2

approved = runner.run(incident, approval_granted=True)
print(json.dumps(approved.to_dict(), indent=2, default=str))
assert approved.remediation.status == "VERIFIED"
assert executor.replicas == 4
