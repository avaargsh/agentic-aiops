import json

from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.models import Incident
from test_golden_incident import build_runner


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


def context(tmp_path, run_id="run-1"):
    return DurableRunContext(run_id, "session-1", artifact_root=tmp_path)


def frozen_approval_id(tmp_path, run_id="run-1"):
    data = json.loads((tmp_path / run_id / "decision.json").read_text())
    return data["ledger"]["attributes"]["approval_id"]


def test_durable_golden_incident_pauses_before_write(tmp_path):
    runtime = Runtime()
    result = build_runner().run_durable(
        Incident("inc-001", "checkout latency", "sev2"),
        runtime=runtime,
        context=context(tmp_path),
    )
    assert result is None
    assert runtime.events[0][0] == "start"
    assert runtime.events[-1][0] == "pause"
    assert runtime.events[-1][1][0].startswith("evidence://sha256/")
    assert (tmp_path / "run-1" / "evidence-bundle.json").exists()
    assert (tmp_path / "run-1" / "decision.json").exists()


def test_durable_golden_incident_resumes_from_exact_approval_and_completes(tmp_path):
    runtime = Runtime()
    runner = build_runner()
    ctx = context(tmp_path)
    incident = Incident("inc-001", "checkout latency", "sev2")

    assert runner.run_durable(incident, runtime=runtime, context=ctx) is None
    runtime.state["approval_events"] = [
        {"approval_id": frozen_approval_id(tmp_path), "approved": True}
    ]
    result = runner.run_durable(incident, runtime=runtime, context=ctx)

    assert result is not None
    assert result.remediation.status == "VERIFIED"
    complete = runtime.events[-1]
    assert complete[0] == "complete"
    assert complete[1]["bundle_sha256"] == result.bundle_sha256
    assert complete[2][0] == f"evidence://sha256/{result.bundle_sha256}"


def test_unrelated_approval_cannot_authorize_frozen_action(tmp_path):
    runtime = Runtime()
    runner = build_runner()
    ctx = context(tmp_path)
    incident = Incident("inc-001", "checkout latency", "sev2")

    assert runner.run_durable(incident, runtime=runtime, context=ctx) is None
    required = frozen_approval_id(tmp_path)
    runtime.state["approval_events"] = [
        {"approval_id": "approval-for-another-action", "approved": True}
    ]

    assert runner.run_durable(incident, runtime=runtime, context=ctx) is None
    assert not (tmp_path / "run-1" / "actions").exists()

    runtime.state["approval_events"].append(
        {"approval_id": required, "approved": True}
    )
    assert runner.run_durable(incident, runtime=runtime, context=ctx) is not None


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

    def counted_decide(proposal, **kwargs):
        nonlocal decision_calls
        decision_calls += 1
        return original_decide(proposal, **kwargs)

    runner.investigation.run = counted_investigation
    runner.orchestrator.decide = counted_decide
    incident = Incident("inc-001", "checkout latency", "sev2")
    ctx = context(tmp_path)

    assert runner.run_durable(incident, runtime=runtime, context=ctx) is None
    assert investigation_calls == 1
    assert decision_calls == 1

    runtime.state["approval_events"] = [
        {"approval_id": frozen_approval_id(tmp_path), "approved": True}
    ]
    result = runner.run_durable(incident, runtime=runtime, context=ctx)

    assert result is not None
    assert result.remediation.status == "VERIFIED"
    assert investigation_calls == 1
    assert decision_calls == 1


def test_golden_incident_contract_preserves_release_run_runtime_and_evidence_identity(tmp_path):
    runtime = Runtime()
    run_id = "golden-checkout-live-001"
    session_id = "session://golden-checkout-live-001"
    release_ref = "release://sre-rca-agent-v1"
    ctx = DurableRunContext(run_id, session_id, artifact_root=tmp_path)
    incident = Incident("inc-001", "checkout latency", "sev2")
    runner = build_runner()

    control_plane_run = {
        "metadata": {"id": run_id},
        "spec": {
            "sessionRef": session_id,
            "releaseRef": release_ref,
            "workflowRef": f"temporal://{run_id}",
            "sandboxRef": f"sandbox://{run_id}",
            "status": "running",
            "evidenceRefs": [],
        },
    }

    assert runner.run_durable(incident, runtime=runtime, context=ctx) is None
    frozen_bundle_ref = runtime.events[-1][1][0]
    control_plane_run["spec"]["status"] = "paused"
    control_plane_run["spec"]["evidenceRefs"] = [frozen_bundle_ref]

    runtime.state["approval_events"] = [
        {"approval_id": frozen_approval_id(tmp_path, run_id), "approved": True}
    ]
    result = runner.run_durable(incident, runtime=runtime, context=ctx)

    assert result is not None
    complete = runtime.events[-1]
    control_plane_run["spec"]["status"] = "succeeded"
    control_plane_run["spec"]["evidenceRefs"] = list(complete[2])

    assert control_plane_run["metadata"]["id"] == run_id
    assert control_plane_run["spec"]["releaseRef"] == release_ref
    assert control_plane_run["spec"]["workflowRef"] == f"temporal://{run_id}"
    assert control_plane_run["spec"]["sandboxRef"] == f"sandbox://{run_id}"
    assert frozen_bundle_ref in control_plane_run["spec"]["evidenceRefs"]
