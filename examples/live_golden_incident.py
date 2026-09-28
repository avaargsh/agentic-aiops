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
from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.temporal_approval import TemporalApprovalRunner
from agentic_aiops.temporal_factory import build_temporal_port

def hypotheses(investigation):
    return [Hypothesis("h-capacity", "checkout-api is capacity constrained", list(investigation.evidence), VerificationStatus.SUPPORTED)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="golden-checkout-live-001")
    parser.add_argument("--session-id", default="golden-demo")
    parser.add_argument("--approval-timeout", type=float, default=300.0)
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
    runtime = build_temporal_port()
    result = TemporalApprovalRunner(runner, runtime, timeout_seconds=args.approval_timeout).run(
        Incident("inc-checkout-live-001", "checkout-api latency above SLO", "sev2", "namespace=golden-demo"),
        context=DurableRunContext(args.run_id, args.session_id),
    )
    print(json.dumps(result.to_dict(), indent=2, default=str))
    if result.remediation.status != "VERIFIED": raise SystemExit(3)

if __name__ == "__main__": main()
