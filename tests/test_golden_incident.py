from datetime import datetime, timezone

from agentic_aiops.action_orchestrator import ActionOrchestrator, ProposedAction
from agentic_aiops.golden_incident import GoldenIncidentRunner
from agentic_aiops.models import Hypothesis, Incident, VerificationStatus
from agentic_aiops.remediation import ExecutionResult, SafeRemediationRunner, VerificationResult, RollbackResult
from agentic_aiops.runner import InvestigationRunner
from agentic_aiops.tools import StaticReadTool

class DecisionClient:
    def decide(self, **kwargs):
        return {"decision": {"candidate": "execute", "confidence": 0.91}}

class Executor:
    def execute(self, action):
        return ExecutionResult(True, action.target, ("e-action",))
    def rollback(self, action, execution):
        return RollbackResult(True, ("e-rollback",))

class Verifier:
    def verify(self, action, execution):
        return VerificationResult(True, ("e-after",), "latency recovered")

def hypotheses(investigation):
    evidence_id = next(iter(investigation.evidence))
    return [Hypothesis("h-load", "load saturation", [evidence_id], VerificationStatus.SUPPORTED)]

def proposal(bundle):
    return ProposedAction(action_kind="scale", target="deployment/checkout-api", blast_radius="single-workload", rollback_available=True, evidence_ids=tuple(item.evidence_id for item in bundle.evidence), description="scale checkout-api from 2 to 4 replicas")

def build_runner():
    return GoldenIncidentRunner(investigation=InvestigationRunner(tools=[StaticReadTool(name="metrics", source="prometheus", observations=["cpu=91 p95=812ms"])], hypothesis_fn=hypotheses), orchestrator=ActionOrchestrator(decision_client=DecisionClient()), remediation=SafeRemediationRunner(executor=Executor(), verifier=Verifier()), proposal_fn=proposal, clock=lambda: datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc))

def test_golden_incident_stops_at_approval_gate():
    result = build_runner().run(Incident("inc-001", "checkout latency", "sev2"))
    assert result.action.approval_required is True
    assert result.remediation.status == "NOT_AUTHORIZED"
    assert [event.phase for event in result.events] == ["incident", "investigation", "decision", "approval", "remediation"]

def test_golden_incident_executes_only_after_approval():
    result = build_runner().run(Incident("inc-001", "checkout latency", "sev2"), approval_granted=True)
    assert result.remediation.status == "VERIFIED"
    assert result.bundle_sha256
    assert "e-after" in result.remediation.evidence_ids
