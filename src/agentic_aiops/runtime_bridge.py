from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from .action_orchestrator import ProposedAction


class RuntimeApprovalAPI(Protocol):
    def request_approval(
        self,
        run_id: str,
        *,
        action: str,
        evidence_refs: Sequence[str] | None = None,
    ) -> Any:
        ...


@dataclass
class RuntimeApprovalSink:
    """Duck-typed bridge to Cloud Agent Runtime approval state."""

    runtime: RuntimeApprovalAPI
    run_id: str
    evidence_uri_prefix: str = "evidence://aiops"

    def request(
        self,
        *,
        action: ProposedAction,
        evidence_ids: Sequence[str],
    ) -> str:
        evidence_refs = [
            f"{self.evidence_uri_prefix}/{evidence_id}"
            for evidence_id in evidence_ids
        ]

        approval = self.runtime.request_approval(
            self.run_id,
            action=(
                action.description
                or f"{action.action_kind} {action.target}"
            ),
            evidence_refs=evidence_refs,
        )

        return f"approval://{approval.approval_id}"
