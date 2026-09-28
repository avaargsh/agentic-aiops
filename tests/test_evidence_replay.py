from agentic_aiops.bundle import EvidenceBundle
from agentic_aiops.models import Evidence, Incident
from agentic_aiops.replay import investigation_from_bundle

def bundle():
    return EvidenceBundle(incident=Incident("inc-001", "latency", "sev2"), evidence=[Evidence("e-1", "prometheus", "p95=812ms")], metadata={"schema_version": "aiops.evidence/v1"})

def test_bundle_hash_is_stable_and_ignores_embedded_hash():
    item = bundle()
    first = item.sha256()
    item.metadata["bundle_sha256"] = first
    assert item.sha256() == first

def test_replay_uses_frozen_bundle_without_live_tools():
    item = bundle()
    replay = investigation_from_bundle(item)
    assert replay.incident.incident_id == "inc-001"
    assert list(replay.evidence) == ["e-1"]
