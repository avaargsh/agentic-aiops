from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    requires_approval: bool
    reason_code: str


class ActionPolicy:
    """Minimal deterministic gate for proposed remediation actions."""

    def evaluate(
        self,
        *,
        action_kind: str,
        blast_radius: str,
        rollback_available: bool,
    ) -> ActionDecision:
        if action_kind == "read":
            return ActionDecision(True, False, "READ_ONLY")

        if blast_radius not in {"single-workload", "single-node"}:
            return ActionDecision(False, True, "WIDE_BLAST_RADIUS")

        if not rollback_available:
            return ActionDecision(False, True, "NO_ROLLBACK")

        return ActionDecision(True, True, "APPROVAL_REQUIRED")
