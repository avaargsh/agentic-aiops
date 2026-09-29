from __future__ import annotations

import json

from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.golden_incident import GoldenIncidentRunner
from agentic_aiops.models import Incident

from test_golden_incident import build_runner


class Run:
    pass


class DurableRuntime:
    def __init__(self):
        self.result = None
        self.evidence_refs = ()
        self.approval_events = []

    def start_or_attach(self, *, runtime_run_id, session_id):
        return Run()

    def status(self, run):
        return {"approval_events": list(self.approval_events)}

    def pause(self, run, *, evidence_refs):
        self.evidence_refs = tuple(evidence_refs)

    def complete(self, run, *, result, evidence_refs):
        self.result = result
        self.evidence_refs = tuple(evidence_refs)


def test_release_identity_is_frozen_and_completed_with_run(tmp_path):
    runner: GoldenIncidentRunner = build_runner()
    runtime = DurableRuntime()
    context = DurableRunContext(
        runtime_run_id="run-001",
        session_id="session-001",
        release_ref="checkout-sre-golden-v1",
        artifact_root=tmp_path,
    )

    incident = Incident("inc-001", "checkout latency", "sev2")
    assert runner.run_durable(
        incident,
        runtime=runtime,
        context=context,
    ) is None
    decision = json.loads(
        (tmp_path / "run-001" / "decision.json").read_text()
    )
    runtime.approval_events = [{
        "approval_id": decision["ledger"]["attributes"]["approval_id"],
        "approved": True,
    }]
    result = runner.run_durable(
        incident,
        runtime=runtime,
        context=context,
    )

    assert result is not None
    frozen = json.loads(
        (tmp_path / "run-001" / "evidence-bundle.json").read_text()
    )
    assert frozen["metadata"]["release_ref"] == "checkout-sre-golden-v1"
    assert frozen["metadata"]["runtime_run_id"] == "run-001"
    decision = json.loads(
        (tmp_path / "run-001" / "decision.json").read_text()
    )
    assert decision["ledger"]["attributes"]["release_ref"] == "checkout-sre-golden-v1"
    assert decision["ledger"]["attributes"]["runtime_run_id"] == "run-001"
    assert decision["ledger"]["attributes"]["evidence_digest"]

    assert runtime.result["release_ref"] == "checkout-sre-golden-v1"
    assert runtime.result["runtime_run_id"] == "run-001"
    assert runtime.evidence_refs[0].startswith("evidence://sha256/")
    assert "artifact://run-001/post-action-evidence.json" in runtime.evidence_refs
    post_action = json.loads(
        (tmp_path / "run-001" / "post-action-evidence.json").read_text()
    )
    assert post_action["status"] == "VERIFIED"
    assert post_action["verification_evidence_ids"]
