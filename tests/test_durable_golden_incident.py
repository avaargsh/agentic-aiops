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

def test_durable_golden_incident_pauses_before_write():
    runtime = Runtime()
    result = build_runner().run_durable(Incident("inc-001", "checkout latency", "sev2"), runtime=runtime, context=DurableRunContext("run-1", "session-1"))
    assert result is None
    assert runtime.events[0][0] == "start"
    assert runtime.events[-1][0] == "pause"
    assert runtime.events[-1][1][0].startswith("evidence://sha256/")

def test_durable_golden_incident_resumes_from_approval_event_and_completes():
    runtime = Runtime()
    runtime.state["approval_events"] = [{"approval_id": "approval-1", "approved": True}]
    result = build_runner().run_durable(Incident("inc-001", "checkout latency", "sev2"), runtime=runtime, context=DurableRunContext("run-1", "session-1"))
    assert result is not None
    assert result.remediation.status == "VERIFIED"
    complete = runtime.events[-1]
    assert complete[0] == "complete"
    assert complete[1]["bundle_sha256"] == result.bundle_sha256
    assert complete[2][0] == f"evidence://sha256/{result.bundle_sha256}"
