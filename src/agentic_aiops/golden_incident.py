from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable

from .action_orchestrator import ActionOrchestrator, OrchestratedAction, ProposedAction
from .bundle import EvidenceBundle
from .models import Incident
from .remediation import RemediationResult, SafeRemediationRunner
from .runner import InvestigationRunner

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
        bundle_sha256 = bundle.sha256()
        bundle.metadata.update({"schema_version": "aiops.evidence/v1", "bundle_sha256": bundle_sha256})
        events.append(self._event("investigation", "collected", evidence_count=len(bundle.evidence), bundle_sha256=bundle_sha256))
        proposal = self.proposal_fn(bundle)
        action = self.orchestrator.decide(proposal)
        events.append(self._event("decision", action.selected_path, confidence=action.model_confidence, approval_required=action.approval_required))
        if action.approval_required:
            events.append(self._event("approval", "granted" if approval_granted else "required"))
        remediation = self.remediation.run(action, approval_granted=approval_granted)
        events.append(self._event("remediation", remediation.status.lower(), evidence_ids=list(remediation.evidence_ids)))
        return GoldenIncidentResult(incident.incident_id, bundle_sha256, action, remediation, tuple(events))
