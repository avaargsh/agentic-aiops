from agentic_aiops.bundle import EvidenceBundle
from agentic_aiops.ledger import DecisionLedgerEntry
from agentic_aiops.models import Incident
from agentic_aiops.provenance import verify_replay_provenance


def fixture():
    bundle = EvidenceBundle(
        Incident("inc-1", "latency", "sev2"),
        metadata={
            "release_ref": "checkout-sre-golden-v1",
            "runtime_run_id": "run-001",
        },
    )
    digest = bundle.sha256()
    ledger = DecisionLedgerEntry(
        decision_type="remediation_escalation",
        selected_action="execute",
        policy_reason="bounded",
        attributes={
            "release_ref": "checkout-sre-golden-v1",
            "runtime_run_id": "run-001",
            "evidence_digest": digest,
        },
    )
    return bundle, ledger


def test_replay_provenance_accepts_same_release_run_and_evidence():
    bundle, ledger = fixture()
    assert verify_replay_provenance(bundle, ledger).valid is True


def test_replay_provenance_rejects_cross_release_decision():
    bundle, ledger = fixture()
    bad = DecisionLedgerEntry(
        decision_type=ledger.decision_type,
        selected_action=ledger.selected_action,
        policy_reason=ledger.policy_reason,
        attributes={
            **dict(ledger.attributes),
            "release_ref": "checkout-sre-golden-v2",
        },
    )
    result = verify_replay_provenance(bundle, bad)
    assert result.valid is False
    assert result.reason == "release_ref mismatch"


def test_replay_provenance_rejects_mutated_evidence():
    bundle, ledger = fixture()
    bundle.metadata["extra"] = "mutated-after-decision"
    result = verify_replay_provenance(bundle, ledger)
    assert result.valid is False
    assert result.reason == "evidence_digest mismatch"
