import json

from agentic_aiops.durable_runtime import DurableRunContext
from agentic_aiops.models import Incident
from test_durable_golden_incident import Runtime
from test_golden_incident import build_runner


def test_release_identity_is_consistent_across_frozen_decision_and_acceptance(tmp_path):
    runtime = Runtime()
    ctx = DurableRunContext(
        "run-golden-001",
        "session-golden-001",
        artifact_root=tmp_path,
        release_ref="checkout-sre-golden-v1",
    )
    runner = build_runner()
    incident = Incident("inc-001", "checkout latency", "sev2")

    # First durable pass must freeze evidence and pause on the exact
    # deterministic approval identity produced for this action.
    assert runner.run_durable(incident, runtime=runtime, context=ctx) is None
    run_dir = tmp_path / ctx.runtime_run_id
    frozen_decision = json.loads((run_dir / "decision.json").read_text())
    approval_id = frozen_decision["ledger"]["attributes"]["approval_id"]
    assert approval_id.startswith("approval-")

    runtime.state["approval_events"] = [
        {"approval_id": approval_id, "approved": True}
    ]
    result = runner.run_durable(incident, runtime=runtime, context=ctx)

    assert result is not None
    bundle = json.loads((run_dir / "evidence-bundle.json").read_text())
    decision = json.loads((run_dir / "decision.json").read_text())
    release = json.loads((run_dir / "release-evidence.json").read_text())
    complete = runtime.events[-1][1]

    assert bundle["metadata"]["release_ref"] == ctx.release_ref
    assert bundle["metadata"]["runtime_run_id"] == ctx.runtime_run_id
    assert decision["ledger"]["attributes"]["release_ref"] == ctx.release_ref
    assert decision["ledger"]["attributes"]["runtime_run_id"] == ctx.runtime_run_id
    assert decision["ledger"]["attributes"]["approval_id"] == approval_id
    assert release["release_ref"] == ctx.release_ref
    assert release["runtime_run_id"] == ctx.runtime_run_id
    assert complete["release_ref"] == ctx.release_ref
    assert complete["runtime_run_id"] == ctx.runtime_run_id

    frozen_digest = bundle["metadata"]["bundle_sha256"]
    assert decision["ledger"]["attributes"]["evidence_digest"] == frozen_digest
    assert release["bundle_sha256"] == frozen_digest
    assert complete["bundle_sha256"] == frozen_digest
