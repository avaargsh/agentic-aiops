from __future__ import annotations

import json

from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.models import Incident
from test_durable_golden_incident import Runtime
from test_golden_incident import build_runner


def test_retry_after_completed_action_reuses_receipt(tmp_path):
    runtime = Runtime()
    runner = build_runner()
    calls = 0
    original = runner.remediation.run

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    runner.remediation.run = counted
    ctx = DurableRunContext(
        "run-001",
        "session-001",
        release_ref="checkout-sre-golden-v1",
        artifact_root=tmp_path,
    )
    incident = Incident("inc-001", "checkout latency", "sev2")

    assert runner.run_durable(
        incident, runtime=runtime, context=ctx
    ) is None
    decision = json.loads(
        (tmp_path / "run-001" / "decision.json").read_text()
    )
    runtime.state["approval_events"] = [{
        "approval_id": decision["ledger"]["attributes"]["approval_id"],
        "approved": True,
    }]
    first = runner.run_durable(
        incident, runtime=runtime, context=ctx
    )
    assert first is not None
    assert calls == 1
    receipts = list((tmp_path / "run-001" / "actions").glob("*.json"))
    assert len(receipts) == 1

    # Simulate a caller retry after the side effect and receipt were durable
    # but before it observed terminal completion.
    runtime.state["phase"] = "running"
    second = runner.run_durable(
        incident, runtime=runtime, context=ctx
    )
    assert second is not None
    assert calls == 1
    assert second.remediation.status == first.remediation.status
