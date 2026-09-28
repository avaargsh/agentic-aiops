from dataclasses import dataclass

from agentic_aiops.action_orchestrator import (
    ActionOrchestrator,
    ProposedAction,
)
from agentic_aiops.runtime_bridge import RuntimeApprovalSink


class DemoDecisionClient:
    def decide(self, **kwargs):
        return {
            "action": "EXECUTE",
            "decision": {
                "candidate": "execute",
                "confidence": 0.94,
            },
        }


@dataclass
class Approval:
    approval_id: str


class DemoRuntime:
    def request_approval(
        self,
        run_id,
        *,
        action,
        evidence_refs=None,
    ):
        print(
            {
                "run_id": run_id,
                "action": action,
                "evidence_refs": evidence_refs,
            }
        )
        return Approval("demo-approval")


sink = RuntimeApprovalSink(
    runtime=DemoRuntime(),
    run_id="run-demo",
)

result = ActionOrchestrator(
    decision_client=DemoDecisionClient(),
    approval_sink=sink,
).decide(
    ProposedAction(
        action_kind="restart",
        target="deployment/checkout",
        blast_radius="single-workload",
        rollback_available=True,
        evidence_ids=("e-db-pool", "e-latency"),
    )
)

print(result)
