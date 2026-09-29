from __future__ import annotations

import json

import pytest

from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.models import Incident
from test_durable_golden_incident import Runtime
from test_golden_incident import build_runner


def freeze(tmp_path):
    runtime = Runtime()
    runner = build_runner()
    ctx = DurableRunContext(
        "run-001",
        "session-001",
        release_ref="checkout-sre-golden-v1",
        artifact_root=tmp_path,
    )
    assert runner.run_durable(
        Incident("inc-001", "checkout latency", "sev2"),
        runtime=runtime,
        context=ctx,
    ) is None
    decision = json.loads(
        (tmp_path / "run-001" / "decision.json").read_text()
    )
    runtime.state["approval_events"] = [{
        "approval_id": decision["ledger"]["attributes"]["approval_id"],
        "approved": True,
    }]
    return runner, runtime, ctx


def test_resume_rejects_release_switch(tmp_path):
    runner, runtime, _ = freeze(tmp_path)
    changed = DurableRunContext(
        "run-001",
        "session-001",
        release_ref="checkout-sre-golden-v2",
        artifact_root=tmp_path,
    )
    with pytest.raises(RuntimeError, match="release_ref"):
        runner.run_durable(
            Incident("inc-001", "checkout latency", "sev2"),
            runtime=runtime,
            context=changed,
        )


def test_resume_rejects_mutated_frozen_evidence(tmp_path):
    runner, runtime, ctx = freeze(tmp_path)
    path = tmp_path / "run-001" / "evidence-bundle.json"
    payload = json.loads(path.read_text())
    payload["metadata"]["unexpected"] = "mutation"
    path.write_text(json.dumps(payload))

    with pytest.raises(RuntimeError, match="evidence_digest"):
        runner.run_durable(
            Incident("inc-001", "checkout latency", "sev2"),
            runtime=runtime,
            context=ctx,
        )


def test_resume_rejects_decision_from_other_run(tmp_path):
    runner, runtime, ctx = freeze(tmp_path)
    path = tmp_path / "run-001" / "decision.json"
    payload = json.loads(path.read_text())
    payload["ledger"]["attributes"]["runtime_run_id"] = "run-999"
    path.write_text(json.dumps(payload))

    with pytest.raises(RuntimeError, match="runtime_run_id"):
        runner.run_durable(
            Incident("inc-001", "checkout latency", "sev2"),
            runtime=runtime,
            context=ctx,
        )
