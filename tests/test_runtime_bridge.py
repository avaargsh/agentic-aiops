from dataclasses import dataclass

from agentic_aiops.action_orchestrator import ProposedAction
from agentic_aiops.runtime_bridge import RuntimeApprovalSink


@dataclass
class Approval:
    approval_id: str


class FakeRuntime:
    def __init__(self):
        self.calls = []

    def request_approval(
        self,
        run_id,
        *,
        action,
        evidence_refs=None,
    ):
        self.calls.append(
            {
                "run_id": run_id,
                "action": action,
                "evidence_refs": list(evidence_refs or []),
            }
        )
        return Approval("approval-123")


def test_runtime_approval_sink_maps_evidence_refs() -> None:
    runtime = FakeRuntime()
    sink = RuntimeApprovalSink(
        runtime=runtime,
        run_id="run-1",
    )

    ref = sink.request(
        action=ProposedAction(
            action_kind="restart",
            target="deployment/checkout",
            blast_radius="single-workload",
            rollback_available=True,
            evidence_ids=("e-1", "e-2"),
            description="restart checkout after verified saturation",
        ),
        evidence_ids=("e-1", "e-2"),
    )

    assert ref == "approval://approval-123"
    assert runtime.calls[0]["run_id"] == "run-1"
    assert runtime.calls[0]["evidence_refs"] == [
        "evidence://aiops/e-1",
        "evidence://aiops/e-2",
    ]



def test_golden_incident_uses_canonical_run_and_evidence_refs() -> None:
    runtime = FakeRuntime()
    run_id = "golden-checkout-live-001"
    sink = RuntimeApprovalSink(runtime=runtime, run_id=run_id)

    ref = sink.request(
        action=ProposedAction(
            action_kind="scale",
            target="deployment/checkout",
            blast_radius="single-workload",
            rollback_available=True,
            evidence_ids=("metrics-before", "decision-001"),
            description="scale checkout after verified saturation",
        ),
        evidence_ids=("metrics-before", "decision-001"),
    )

    assert ref == "approval://approval-123"
    assert runtime.calls == [
        {
            "run_id": run_id,
            "action": "scale checkout after verified saturation",
            "evidence_refs": [
                "evidence://aiops/metrics-before",
                "evidence://aiops/decision-001",
            ],
        }
    ]
