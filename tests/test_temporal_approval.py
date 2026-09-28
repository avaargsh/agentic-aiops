from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.temporal_approval import TemporalApprovalRunner

class Runtime:
    def __init__(self, states): self.states=list(states); self.starts=0
    def start_or_attach(self, **kwargs): self.starts += 1; return "run"
    def status(self, run): return self.states.pop(0) if len(self.states)>1 else self.states[0]

class Runner:
    def __init__(self): self.calls=0
    def run_durable(self, incident, *, runtime, context):
        self.calls += 1
        return None if self.calls == 1 else "VERIFIED"

def test_no_approval_never_resumes_write_path():
    runtime=Runtime([{"approval_events": []}])
    runner=Runner()
    try:
        TemporalApprovalRunner(runner, runtime, poll_seconds=0, timeout_seconds=0).run(object(), context=DurableRunContext("run-1","s-1"))
    except TimeoutError: pass
    else: raise AssertionError("expected timeout")
    assert runner.calls == 1

def test_approved_signal_resumes_exactly_once():
    runtime=Runtime([{"approval_events": [{"approval_id":"a1","approved":True},{"approval_id":"a1","approved":True}]}])
    runner=Runner()
    result=TemporalApprovalRunner(runner, runtime, poll_seconds=0, timeout_seconds=1).run(object(), context=DurableRunContext("run-1","s-1"))
    assert result == "VERIFIED"
    assert runner.calls == 2

def test_denied_signal_never_resumes():
    runtime=Runtime([{"approval_events": [{"approval_id":"a1","approved":False}]}])
    runner=Runner()
    try:
        TemporalApprovalRunner(runner, runtime, poll_seconds=0, timeout_seconds=1).run(object(), context=DurableRunContext("run-1","s-1"))
    except RuntimeError as exc: assert "denied" in str(exc)
    else: raise AssertionError("expected denial")
    assert runner.calls == 1
