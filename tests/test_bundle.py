from pathlib import Path

from agentic_aiops.bundle import EvidenceBundle
from agentic_aiops.models import (
    ChangeEvent,
    Evidence,
    Hypothesis,
    Incident,
    TopologyEdge,
    TopologyEntity,
    VerificationStatus,
)
from agentic_aiops.replay import investigation_from_bundle


def test_evidence_bundle_round_trip(tmp_path: Path) -> None:
    bundle = EvidenceBundle(
        incident=Incident(
            incident_id="inc-1",
            summary="checkout latency",
            severity="sev2",
            scope="service=checkout",
        ),
        evidence=[
            Evidence(
                evidence_id="e-1",
                source="prometheus",
                observation="p99 latency > 1s",
                entity_refs=("svc-checkout",),
            )
        ],
        hypotheses=[
            Hypothesis(
                hypothesis_id="h-1",
                statement="downstream saturation",
                evidence_ids=["e-1"],
                status=VerificationStatus.SUPPORTED,
            )
        ],
        entities=[
            TopologyEntity(
                entity_id="svc-checkout",
                kind="service",
                name="checkout",
            ),
            TopologyEntity(
                entity_id="db-orders",
                kind="database",
                name="orders",
            ),
        ],
        edges=[
            TopologyEdge(
                source="svc-checkout",
                target="db-orders",
                relation="depends_on",
            )
        ],
        changes=[
            ChangeEvent(
                change_id="chg-1",
                entity_id="svc-checkout",
                kind="deployment",
                summary="checkout v42 deployed",
            )
        ],
    )

    path = tmp_path / "bundle.json"
    bundle.write_json(path)
    loaded = EvidenceBundle.read_json(path)

    assert loaded.incident.incident_id == "inc-1"
    assert loaded.evidence[0].entity_refs == ("svc-checkout",)
    assert loaded.hypotheses[0].status == VerificationStatus.SUPPORTED
    assert loaded.edges[0].relation == "depends_on"


def test_bundle_replays_into_investigation() -> None:
    bundle = EvidenceBundle(
        incident=Incident("inc-1", "latency", "sev2"),
        evidence=[
            Evidence("e-1", "prometheus", "cpu normal"),
        ],
        hypotheses=[
            Hypothesis("h-1", "not cpu bound"),
        ],
    )

    investigation = investigation_from_bundle(bundle)

    assert "e-1" in investigation.evidence
    assert "h-1" in investigation.hypotheses
