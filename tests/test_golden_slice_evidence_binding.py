from datetime import datetime, timezone

from agentic_aiops.action_orchestrator import ActionOrchestrator, ProposedAction
from agentic_aiops.golden_incident import GoldenIncidentRunner
from agentic_aiops.models import Hypothesis, Incident, VerificationStatus
from agentic_aiops.remediation import ExecutionResult, RollbackResult, SafeRemediationRunner, VerificationResult
from agentic_aiops.runner import InvestigationRunner
from agentic_aiops.tools import StaticReadTool


class RecordingDecisionClient:
    def __init__(self):
        self.request = None

    def decide(self, **kwargs):
        self.request = kwargs
        return {"decision": {"candidate": "execute", "confidence": 0.91}}


class Executor:
    def execute(self, action):
        return ExecutionResult(True, action.target, ("e-action",))
    def rollback(self, action, execution):
        return RollbackResult(True, ("e-rollback",))


class Verifier:
    def verify(self, action, execution):
        return VerificationResult(True, ("e-after",), "recovered")


def test_decision_request_is_bound_to_exact_frozen_evidence_digest():
    client = RecordingDecisionClient()
    runner = GoldenIncidentRunner(
        investigation=InvestigationRunner(
            tools=[StaticReadTool(name="metrics", source="prometheus", observations=["p95=812ms"])],
            hypothesis_fn=lambda investigation: [Hypothesis("h1", "latency", [next(iter(investigation.evidence))], VerificationStatus.SUPPORTED)],
        ),
        orchestrator=ActionOrchestrator(decision_client=client),
        remediation=SafeRemediationRunner(executor=Executor(), verifier=Verifier()),
        proposal_fn=lambda bundle: ProposedAction("scale", "deployment/checkout", "single-workload", True, tuple(item.evidence_id for item in bundle.evidence)),
        clock=lambda: datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    result = runner.run(Incident("inc-001", "checkout latency", "sev2"))
    assert client.request["context"]["evidence_digest"] == result.bundle_sha256
    assert result.action.ledger.attributes["evidence_digest"] == result.bundle_sha256
