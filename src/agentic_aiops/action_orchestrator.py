from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .decision_client import DecisionClient
from .ledger import DecisionLedgerEntry
from .policy import ActionDecision, ActionPolicy


@dataclass(frozen=True)
class ProposedAction:
    action_kind: str
    target: str
    blast_radius: str
    rollback_available: bool
    evidence_ids: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True)
class OrchestratedAction:
    proposal: ProposedAction
    selected_path: str
    model_confidence: float | None
    policy: ActionDecision
    execution_allowed: bool
    approval_required: bool
    ledger: DecisionLedgerEntry


class ApprovalSink(Protocol):
    def request(
        self,
        *,
        action: ProposedAction,
        evidence_ids: Sequence[str],
    ) -> str:
        ...


class ActionOrchestrator:
    """Combine learned routing with deterministic action authorization."""

    _CANDIDATES = [
        "execute",
        "fallback",
        "human_review",
    ]

    def __init__(
        self,
        *,
        decision_client: DecisionClient,
        policy: ActionPolicy | None = None,
        approval_sink: ApprovalSink | None = None,
    ) -> None:
        self.decision_client = decision_client
        self.policy = policy or ActionPolicy()
        self.approval_sink = approval_sink

    def decide(
        self,
        proposal: ProposedAction,
        *,
        evidence_digest: str | None = None,
    ) -> OrchestratedAction:
        response = self.decision_client.decide(
            decision_type="escalation",
            candidates=list(self._CANDIDATES),
            context={
                "action_kind": proposal.action_kind,
                "target": proposal.target,
                "blast_radius": proposal.blast_radius,
                "rollback_available": proposal.rollback_available,
                "evidence_count": len(proposal.evidence_ids),
                "evidence_digest": evidence_digest,
            },
        )

        selected_path = "fallback"
        confidence = None

        decision = response.get("decision")
        if decision is not None:
            selected_path = str(decision["candidate"])
            confidence = float(
                decision.get("confidence", 0.0)
            )
        elif response.get("action") == "FALLBACK":
            selected_path = "fallback"

        policy = self.policy.evaluate(
            action_kind=proposal.action_kind,
            blast_radius=proposal.blast_radius,
            rollback_available=proposal.rollback_available,
        )

        execution_allowed = (
            selected_path == "execute"
            and policy.allowed
            and not policy.requires_approval
        )

        approval_required = (
            selected_path == "human_review"
            or (
                selected_path == "execute"
                and policy.requires_approval
            )
        )

        if selected_path == "execute" and not policy.allowed:
            approval_required = True
            execution_allowed = False

        approval_ref = None
        if approval_required and self.approval_sink is not None:
            approval_ref = self.approval_sink.request(
                action=proposal,
                evidence_ids=proposal.evidence_ids,
            )

        ledger = DecisionLedgerEntry(
            decision_type="remediation_escalation",
            selected_action=selected_path,
            policy_reason=policy.reason_code,
            evidence_ids=proposal.evidence_ids,
            confidence=confidence,
            requires_approval=approval_required,
            outcome=(
                "AUTHORIZED"
                if execution_allowed
                else (
                    "APPROVAL_REQUIRED"
                    if approval_required
                    else "NO_EXECUTION"
                )
            ),
            attributes={
                "target": proposal.target,
                "blast_radius": proposal.blast_radius,
                "approval_ref": approval_ref or "",
                "evidence_digest": evidence_digest or "",
            },
        )

        return OrchestratedAction(
            proposal=proposal,
            selected_path=selected_path,
            model_confidence=confidence,
            policy=policy,
            execution_allowed=execution_allowed,
            approval_required=approval_required,
            ledger=ledger,
        )
