from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, Sequence

from .decision_client import DecisionClient
from .ledger import DecisionLedgerEntry
from .policy import ActionDecision, ActionPolicy
from .sre_recommendation import SREDecisionRecommendation, validate_sre_recommendation


@dataclass(frozen=True)
class ProposedAction:
    action_kind: str
    target: str
    blast_radius: str
    rollback_available: bool
    evidence_ids: tuple[str, ...] = ()
    description: str | None = None
    # Identity is supplied by the trusted proposal/run builder, not the model.
    change_id: str | None = None


@dataclass(frozen=True)
class OrchestratedAction:
    proposal: ProposedAction
    selected_path: str
    model_confidence: float | None
    decision_id: str | None
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


def _validated_model_confidence(value: object) -> float:
    """Validate provider output before storing it in the decision ledger."""
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
    ):
        raise ValueError("model confidence must be a finite numeric value in [0, 1]")
    return float(value)


def _sre_execution_override(
    recommendation: SREDecisionRecommendation | None,
) -> tuple[str | None, ActionDecision | None]:
    """Return a non-authorizing route/policy override for restrictive SRE advice."""
    if recommendation is None or recommendation.action == "allow":
        return None, None
    if recommendation.action == "reject":
        return "fallback", ActionDecision(
            allowed=False,
            requires_approval=False,
            reason_code="SRE_REJECT_RECOMMENDATION",
        )
    if recommendation.action == "human_review":
        return "human_review", ActionDecision(
            allowed=False,
            requires_approval=True,
            reason_code="SRE_REQUIRES_HUMAN_REVIEW",
        )
    if recommendation.action == "canary":
        return "human_review", ActionDecision(
            allowed=False,
            requires_approval=True,
            reason_code="SRE_CANARY_REQUIRES_DEDICATED_EXECUTOR",
        )
    raise ValueError(f"unsupported validated SRE action: {recommendation.action}")


class ActionOrchestrator:
    """Combine learned routing, optional SRE vetoes, and deterministic authorization.

    The SRE recommendation can only constrain the generic decision path. An
    allow recommendation never upgrades a model fallback, and neither source
    grants execution authority outside the deterministic action policy.
    """

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
        change_id: str | None = None,
        sre_recommendation: Mapping[str, object] | None = None,
    ) -> OrchestratedAction:
        active_change_id = proposal.change_id
        if change_id is not None:
            if not isinstance(change_id, str) or not change_id.strip():
                raise ValueError("change_id must be a non-empty string")
            if active_change_id is not None and active_change_id != change_id:
                raise ValueError("change_id does not match proposal.change_id")
            active_change_id = change_id

        validated_sre: SREDecisionRecommendation | None = None
        if sre_recommendation is not None:
            if not isinstance(proposal.change_id, str) or not proposal.change_id.strip():
                raise ValueError("proposal.change_id is required when an SRE recommendation is supplied")
            if active_change_id != proposal.change_id:
                raise ValueError("change_id does not match proposal.change_id")
            validated_sre = validate_sre_recommendation(
                sre_recommendation,
                expected_change_id=proposal.change_id,
                available_evidence_ids=proposal.evidence_ids,
            )

        # Restrictive SRE advice short-circuits model inference; "allow" does not.
        override_path, override_policy = _sre_execution_override(validated_sre)
        if override_path is not None:
            selected_path = override_path
            confidence = None
            decision_id = None
        else:
            context: dict[str, object] = {
                "action_kind": proposal.action_kind,
                "target": proposal.target,
                "blast_radius": proposal.blast_radius,
                "rollback_available": proposal.rollback_available,
                "evidence_count": len(proposal.evidence_ids),
                "evidence_digest": evidence_digest,
            }
            if active_change_id is not None:
                context["change_id"] = active_change_id

            response = self.decision_client.decide(
                decision_type="escalation",
                candidates=list(self._CANDIDATES),
                context=context,
            )
            if not isinstance(response, Mapping):
                raise ValueError("decision response must be an object")

            selected_path = "fallback"
            confidence = None
            decision_id = (
                str(response["decision_id"])
                if response.get("decision_id")
                else None
            )

            decision = response.get("decision")
            if decision is not None:
                if not isinstance(decision, Mapping):
                    raise ValueError("decision payload must be an object")
                candidate = decision.get("candidate")
                if isinstance(candidate, str) and candidate in self._CANDIDATES:
                    selected_path = candidate
                    confidence = _validated_model_confidence(
                        decision.get("confidence", 0.0)
                    )
            elif response.get("action") == "FALLBACK":
                selected_path = "fallback"

        policy = override_policy or self.policy.evaluate(
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

        attributes = {
            "target": proposal.target,
            "blast_radius": proposal.blast_radius,
            "approval_ref": approval_ref or "",
            "evidence_digest": evidence_digest or "",
            "decision_id": decision_id or "",
            "change_id": active_change_id or "",
        }
        if validated_sre is not None:
            serialized_sre = json.dumps(
                validated_sre.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            attributes.update(
                {
                    "sre_action": validated_sre.action,
                    "sre_reason_code": validated_sre.reason_code,
                    "sre_policy_version": validated_sre.policy_version,
                    "sre_recommendation_sha256": hashlib.sha256(
                        serialized_sre.encode("utf-8")
                    ).hexdigest(),
                    "sre_recommendation_json": serialized_sre,
                }
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
            attributes=attributes,
        )

        return OrchestratedAction(
            proposal=proposal,
            selected_path=selected_path,
            model_confidence=confidence,
            decision_id=decision_id,
            policy=policy,
            execution_allowed=execution_allowed,
            approval_required=approval_required,
            ledger=ledger,
        )
