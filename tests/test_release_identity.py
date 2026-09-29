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

    def start_or_attach(self, *, runtime_run_id, session_id):
        return Run()

    def status(self, run):
        return {
            "approval_events": [
                {"approval_id": "approval-001", "approved": True}
            ]
        }

    def pause(self, run, *, evidence_refs):
        raise AssertionError("approved fixture must not pause")

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

    result = runner.run_durable(
        Incident("inc-001", "checkout latency", "sev2"),
        runtime=runtime,
        context=context,
    )

    assert result is not None
    frozen = json.loads(
        (tmp_path / "run-001" / "evidence-bundle.json").read_text()
    )
    assert frozen["metadata"]["release_ref"] == "checkout-sre-golden-v1"
    assert frozen["metadata"]["runtime_run_id"] == "run-001"
    assert runtime.result["release_ref"] == "checkout-sre-golden-v1"
    assert runtime.result["runtime_run_id"] == "run-001"
    assert runtime.evidence_refs[0].startswith("evidence://sha256/")
