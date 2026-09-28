from agentic_aiops.durable_runtime import DurableRunContext
from test_golden_incident import build_runner
from agentic_aiops.models import Incident

class Runtime:
    def __init__(self):
        self.events = []
        self.state = {"phase": "running", "approval_events": []}
    def start_or_attach(self, **kwargs):
        self.events.append(("start", kwargs))
        return "workflow-1"
    def pause(self, run, *, evidence_refs):
        self.events.append(("pause", tuple(evidence_refs)))
        self.state["phase"] = "paused"
    def status(self, run):
        return dict(self.state)
    def complete(self, run, *, result, evidence_refs):
        self.events.append(("complete", result, tuple(evidence_refs)))
        self.state["phase"] = "succeeded"

def context(tmp_path):
    return DurableRunContext("run-1", "session-1", artifact_root=tmp_path)

def test_durable_golden_incident_pauses_before_write(tmp_path):
    runtime = Runtime()
    result = build_runner().run_durable(Incident("inc-001", "checkout latency", "sev2"), runtime=runtime, context=context(tmp_path))
    assert result is None
    assert runtime.events[0][0] == "start"
    assert runtime.events[-1][0] == "pause"
    assert runtime.events[-1][1][0].startswith("evidence://sha256/")
    assert (tmp_path / "run-1" / "evidence-bundle.json").exists()
    assert (tmp_path / "run-1" / "decision.json").exists()

def test_durable_golden_incident_resumes_from_approval_event_and_completes(tmp_path):
    runtime = Runtime()
    runtime.state["approval_events"] = [{"approval_id": "approval-1", "approved": True}]
    result = build_runner().run_durable(Incident("inc-001", "checkout latency", "sev2"), runtime=runtime, context=context(tmp_path))
    assert result is not None
    assert result.remediation.status == "VERIFIED"
    complete = runtime.events[-1]
    assert complete[0] == "complete"
    assert complete[1]["bundle_sha256"] == result.bundle_sha256
    assert complete[2][0] == f"evidence://sha256/{result.bundle_sha256}"

def test_continue_uses_frozen_evidence_and_decision_without_live_reread(tmp_path):
    runtime = Runtime()
    runner = build_runner()
    investigation_calls = 0
    decision_calls = 0
    original_investigation = runner.investigation.run
    original_decide = runner.orchestrator.decide

    def counted_investigation(incident):
        nonlocal investigation_calls
        investigation_calls += 1
        return original_investigation(incident)

    def counted_decide(proposal):
        nonlocal decision_calls
        decision_calls += 1
        return original_decide(proposal)

    runner.investigation.run = counted_investigation
    runner.orchestrator.decide = counted_decide
    incident = Incident("inc-001", "checkout latency", "sev2")
    ctx = context(tmp_path)

    assert runner.run_durable(incident, runtime=runtime, context=ctx) is None
    assert investigation_calls == 1
    assert decision_calls == 1

    runtime.state["approval_events"] = [{"approval_id": "approval-1", "approved": True}]
    result = runner.run_durable(incident, runtime=runtime, context=ctx)

    assert result is not None
    assert result.remediation.status == "VERIFIED"
    assert investigation_calls == 1
    assert decision_calls == 1
