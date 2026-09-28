from __future__ import annotations

import argparse
import json
import os

from agentic_aiops.action_orchestrator import ActionOrchestrator, ProposedAction
from agentic_aiops.decision_client import HttpDecisionClient
from agentic_aiops.kubernetes_tool import KubernetesListTool
from agentic_aiops.live_remediation import KubectlScaleExecutor, PrometheusPostActionVerifier
from agentic_aiops.models import Hypothesis, Incident, VerificationStatus
from agentic_aiops.prometheus_tool import PrometheusQuery, PrometheusReadTool
from agentic_aiops.remediation import SafeRemediationRunner
from agentic_aiops.runner import InvestigationRunner
from agentic_aiops.golden_incident import GoldenIncidentRunner

def hypotheses(investigation):
    return [Hypothesis("h-capacity", "checkout-api is capacity constrained", list(investigation.evidence), VerificationStatus.SUPPORTED)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approved", action="store_true", help="execute the write path; omit to prove approval gate")
    parser.add_argument("--prometheus", default=os.environ.get("PROMETHEUS_URL", "http://127.0.0.1:19090"))
    parser.add_argument("--kube-api", default=os.environ.get("KUBERNETES_API", "http://127.0.0.1:18001"))
    parser.add_argument("--decision", default=os.environ.get("DECISION_GATEWAY_URL", "http://127.0.0.1:8080"))
    args = parser.parse_args()
    investigation = InvestigationRunner(tools=[
        PrometheusReadTool(args.prometheus, [
            PrometheusQuery("latency", "max(checkout_request_latency_seconds)"),
            PrometheusQuery("active", "sum(checkout_active_requests)"),
            PrometheusQuery("requests", "sum(checkout_requests_total)"),
        ]),
        KubernetesListTool(args.kube_api, "/api/v1/namespaces/{namespace}/pods"),
    ], hypothesis_fn=hypotheses)
    remediation = SafeRemediationRunner(executor=KubectlScaleExecutor(), verifier=PrometheusPostActionVerifier(args.prometheus))
    runner = GoldenIncidentRunner(investigation=investigation, orchestrator=ActionOrchestrator(decision_client=HttpDecisionClient(args.decision)), remediation=remediation, proposal_fn=lambda bundle: ProposedAction("scale", "deployment/checkout-api", "single-workload", True, tuple(e.evidence_id for e in bundle.evidence), "scale checkout-api from 2 to 4 replicas"))
    result = runner.run(Incident("inc-checkout-live-001", "checkout-api latency above SLO", "sev2", "namespace=golden-demo"), approval_granted=args.approved)
    print(json.dumps(result.to_dict(), indent=2, default=str))
    if not args.approved and result.remediation.status != "NOT_AUTHORIZED": raise SystemExit(2)
    if args.approved and result.remediation.status != "VERIFIED": raise SystemExit(3)

if __name__ == "__main__": main()
