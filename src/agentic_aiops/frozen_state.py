from __future__ import annotations

from dataclasses import asdict
import json

from .action_orchestrator import OrchestratedAction, ProposedAction
from .bundle import EvidenceBundle
from .durable_runtime import DurableRunContext
from .ledger import DecisionLedgerEntry
from .policy import ActionDecision


def freeze_frozen_state(
    context: DurableRunContext,
    bundle: EvidenceBundle,
    action: OrchestratedAction,
) -> None:
    """Persist the immutable evidence/decision inputs for durable continuation."""

    run_dir = context.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    bundle.write_json(run_dir / "evidence-bundle.json")
    (run_dir / "decision.json").write_text(
        json.dumps(asdict(action), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_frozen_state(
    context: DurableRunContext,
) -> tuple[EvidenceBundle, OrchestratedAction] | None:
    """Load frozen evidence/decision state without consulting live dependencies."""

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
