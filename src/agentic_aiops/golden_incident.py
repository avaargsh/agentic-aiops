from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Callable

from .durable_runtime import DurableRunContext, DurableRunPort

from .action_orchestrator import ActionOrchestrator, OrchestratedAction, ProposedAction
from .bundle import EvidenceBundle
from .models import Incident
from .policy import ActionDecision
from .ledger import DecisionLedgerEntry
from .remediation import RemediationResult, SafeRemediationRunner
from .runner import InvestigationRunner
from .release_acceptance import write_control_plane_acceptance
from .action_receipt import action_key, load_receipt, store_receipt

@dataclass(frozen=True)
class GoldenIncidentEvent:
    phase: str
    status: str
    at: str
    attributes: dict[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class GoldenIncidentResult:
    incident_id: str
    bundle_sha256: str
    action: OrchestratedAction
    remediation: RemediationResult
    events: tuple[GoldenIncidentEvent, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "bundle_sha256": self.bundle_sha256,
            "action": asdict(self.action),
            "remediation": asdict(self.remediation),
            "events": [asdict(item) for item in self.events],
        }

class GoldenIncidentRunner:
    """Evidence-first incident slice: investigate -> decide -> act -> verify."""

    def __init__(self, *, investigation: InvestigationRunner, orchestrator: ActionOrchestrator, remediation: SafeRemediationRunner, proposal_fn: Callable[[EvidenceBundle], ProposedAction], clock: Callable[[], datetime] | None = None) -> None:
        self.investigation = investigation
        self.orchestrator = orchestrator
        self.remediation = remediation
        self.proposal_fn = proposal_fn
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _event(self, phase: str, status: str, **attributes: object) -> GoldenIncidentEvent:
        return GoldenIncidentEvent(phase=phase, status=status, at=self.clock().isoformat(), attributes=attributes)

    def run(self, incident: Incident, *, approval_granted: bool = False) -> GoldenIncidentResult:
        events = [self._event("incident", "received", severity=incident.severity)]
        investigation = self.investigation.run(incident)
        bundle = investigation.bundle
        bundle.metadata["schema_version"] = "aiops.evidence/v1"
        bundle_sha256 = bundle.sha256()
        bundle.metadata["bundle_sha256"] = bundle_sha256
        events.append(self._event("investigation", "collected", evidence_count=len(bundle.evidence), bundle_sha256=bundle_sha256))
        proposal = self.proposal_fn(bundle)
        action = self.orchestrator.decide(proposal, evidence_digest=bundle_sha256)
        events.append(self._event("decision", action.selected_path, confidence=action.model_confidence, approval_required=action.approval_required))
        if action.approval_required:
            events.append(self._event("approval", "granted" if approval_granted else "required"))
        remediation = self.remediation.run(action, approval_granted=approval_granted)
        events.append(self._event("remediation", remediation.status.lower(), evidence_ids=list(remediation.evidence_ids)))
        return GoldenIncidentResult(incident.incident_id, bundle_sha256, action, remediation, tuple(events))

    def _freeze(self, context: DurableRunContext, bundle: EvidenceBundle, action: OrchestratedAction) -> None:
        run_dir = context.run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        bundle.write_json(run_dir / "evidence-bundle.json")
        (run_dir / "decision.json").write_text(
            json.dumps(asdict(action), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_frozen(self, context: DurableRunContext) -> tuple[EvidenceBundle, OrchestratedAction] | None:
        bundle_path = context.run_dir / "evidence-bundle.json"
        decision_path = context.run_dir / "decision.json"
        if not bundle_path.exists() or not decision_path.exists():
            return None
        bundle = EvidenceBundle.read_json(bundle_path)
        data = json.loads(decision_path.read_text(encoding="utf-8"))
        proposal_data = data["proposal"]
        proposal = ProposedAction(
            action_kind=proposal_data["action_kind"],
            target=proposal_data["target"],
            blast_radius=proposal_data["blast_radius"],
            rollback_available=proposal_data["rollback_available"],
            evidence_ids=tuple(proposal_data.get("evidence_ids", ())),
            description=proposal_data.get("description"),
        )
        policy = ActionDecision(**data["policy"])
        ledger_data = data["ledger"]
        ledger = DecisionLedgerEntry(
            decision_type=ledger_data["decision_type"],
            selected_action=ledger_data["selected_action"],
            policy_reason=ledger_data["policy_reason"],
            evidence_ids=tuple(ledger_data.get("evidence_ids", ())),
            confidence=ledger_data.get("confidence"),
            requires_approval=ledger_data.get("requires_approval", False),
            outcome=ledger_data.get("outcome"),
            attributes=dict(ledger_data.get("attributes", {})),
        )
        return bundle, OrchestratedAction(
            proposal=proposal,
            selected_path=data["selected_path"],
            model_confidence=data.get("model_confidence"),
            decision_id=data.get("decision_id"),
            policy=policy,
            execution_allowed=data["execution_allowed"],
            approval_required=data["approval_required"],
            ledger=ledger,
        )

    def run_durable(
        self,
        incident: Incident,
        *,
        runtime: DurableRunPort,
        context: DurableRunContext,
    ) -> GoldenIncidentResult | None:
        run = runtime.start_or_attach(
            runtime_run_id=context.runtime_run_id,
            session_id=context.session_id,
        )

        frozen = self._load_frozen(context)
        if frozen is None:
            investigation = self.investigation.run(incident)
            bundle = investigation.bundle
            bundle.metadata["schema_version"] = "aiops.evidence/v1"
            if context.release_ref:
                bundle.metadata["release_ref"] = context.release_ref
                bundle.metadata["runtime_run_id"] = context.runtime_run_id
            bundle_sha256 = bundle.sha256()
            bundle.metadata["bundle_sha256"] = bundle_sha256
            proposal = self.proposal_fn(bundle)
            action = self.orchestrator.decide(
                proposal,
                evidence_digest=bundle_sha256,
            )
            if context.release_ref:
                action = OrchestratedAction(
                    proposal=action.proposal,
                    selected_path=action.selected_path,
                    model_confidence=action.model_confidence,
                    decision_id=action.decision_id,
                    policy=action.policy,
                    execution_allowed=action.execution_allowed,
                    approval_required=action.approval_required,
                    ledger=DecisionLedgerEntry(
                        decision_type=action.ledger.decision_type,
                        selected_action=action.ledger.selected_action,
                        policy_reason=action.ledger.policy_reason,
                        evidence_ids=action.ledger.evidence_ids,
                        confidence=action.ledger.confidence,
                        requires_approval=action.ledger.requires_approval,
                        outcome=action.ledger.outcome,
                        attributes={
                            **dict(action.ledger.attributes),
                            "release_ref": context.release_ref,
                            "runtime_run_id": context.runtime_run_id,
                        },
                    ),
                )
            if action.approval_required:
                approval_id = "approval-" + action_key(
                    runtime_run_id=context.runtime_run_id,
                    action=action,
                )[:24]
                action = OrchestratedAction(
                    proposal=action.proposal,
                    selected_path=action.selected_path,
                    model_confidence=action.model_confidence,
                    decision_id=action.decision_id,
                    policy=action.policy,
                    execution_allowed=action.execution_allowed,
                    approval_required=action.approval_required,
                    ledger=DecisionLedgerEntry(
                        decision_type=action.ledger.decision_type,
                        selected_action=action.ledger.selected_action,
                        policy_reason=action.ledger.policy_reason,
                        evidence_ids=action.ledger.evidence_ids,
                        confidence=action.ledger.confidence,
                        requires_approval=action.ledger.requires_approval,
                        outcome=action.ledger.outcome,
                        attributes={
                            **dict(action.ledger.attributes),
                            "approval_id": approval_id,
                        },
                    ),
                )
            self._freeze(context, bundle, action)
        else:
            bundle, action = frozen
            bundle_sha256 = bundle.sha256()
            frozen_release = bundle.metadata.get("release_ref")
            frozen_run = bundle.metadata.get("runtime_run_id")
            if context.release_ref and frozen_release != context.release_ref:
                raise RuntimeError(
                    "frozen evidence release_ref does not match durable run context"
                )
            if frozen_run and frozen_run != context.runtime_run_id:
                raise RuntimeError(
                    "frozen evidence runtime_run_id does not match durable run context"
                )
            ledger_attrs = dict(action.ledger.attributes)
            if frozen_release and ledger_attrs.get("release_ref") != frozen_release:
                raise RuntimeError(
                    "decision ledger release_ref does not match frozen evidence"
                )
            if frozen_run and ledger_attrs.get("runtime_run_id") != frozen_run:
                raise RuntimeError(
                    "decision ledger runtime_run_id does not match frozen evidence"
                )
            if ledger_attrs.get("evidence_digest") != bundle_sha256:
                raise RuntimeError(
                    "decision ledger evidence_digest does not match frozen evidence"
                )

        bundle_ref = context.bundle_ref(bundle_sha256)
        state = runtime.status(run)
        approval_events = list(state.get("approval_events") or [])
        required_approval_id = (
            str(action.ledger.attributes.get("approval_id") or "")
            if action.approval_required
            else ""
        )
        approved = any(
            event.get("approved") is True
            and (
                not required_approval_id
                or event.get("approval_id") == required_approval_id
            )
            for event in approval_events
        )
        denied = any(
            event.get("approved") is False
            and (
                not required_approval_id
                or event.get("approval_id") == required_approval_id
            )
            for event in approval_events
        )

        if denied:
            return None

        if action.approval_required and not approved:
            runtime.pause(run, evidence_refs=(bundle_ref,))
            return None

        key = action_key(
            runtime_run_id=context.runtime_run_id,
            action=action,
        )
        result = load_receipt(context.run_dir, key)
        if result is None:
            result = self.remediation.run(
                action,
                approval_granted=approved,
            )
            store_receipt(context.run_dir, key, result)
        post_action = {
            "status": result.status,
            "execution_evidence_ids": list(
                result.execution.evidence_ids
                if result.execution is not None else ()
            ),
            "verification_evidence_ids": list(
                result.verification.evidence_ids
                if result.verification is not None else ()
            ),
            "verification_summary": (
                result.verification.summary
                if result.verification is not None else None
            ),
            "rollback_evidence_ids": list(
                result.rollback.evidence_ids
                if result.rollback is not None else ()
            ),
        }
        run_dir = context.run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "post-action-evidence.json").write_text(
            json.dumps(post_action, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        post_action_ref = (
            f"artifact://{context.runtime_run_id}/post-action-evidence.json"
        )

        if context.release_ref:
            write_control_plane_acceptance(
                run_dir,
                release_ref=context.release_ref,
                runtime_run_id=context.runtime_run_id,
                bundle_sha256=bundle_sha256,
                remediation_status=result.status,
                post_action_ref=post_action_ref,
            )

        runtime.complete(
            run,
            result={
                "incident_id": incident.incident_id,
                "bundle_sha256": bundle_sha256,
                "decision": action.selected_path,
                "remediation_status": result.status,
                "release_ref": context.release_ref,
                "runtime_run_id": context.runtime_run_id,
            },
            evidence_refs=(
                bundle_ref,
                post_action_ref,
                *result.evidence_ids,
            ),
        )

        return GoldenIncidentResult(
            incident.incident_id,
            bundle_sha256,
            action,
            result,
            (
                self._event("incident", "received"),
                self._event("investigation", "collected", bundle_sha256=bundle_sha256),
                self._event("approval", "granted" if approved else "not_required"),
                self._event("remediation", result.status.lower()),
            ),
        )
