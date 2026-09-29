from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .bundle import EvidenceBundle
from .ledger import DecisionLedgerEntry


@dataclass(frozen=True)
class ProvenanceCheck:
    valid: bool
    release_ref: str | None
    runtime_run_id: str | None
    evidence_digest: str
    reason: str | None = None


def verify_replay_provenance(
    bundle: EvidenceBundle,
    ledger: DecisionLedgerEntry,
) -> ProvenanceCheck:
    """Verify replay inputs belong to one frozen release/run/evidence chain."""
    digest = bundle.sha256()
    release_ref = bundle.metadata.get("release_ref")
    runtime_run_id = bundle.metadata.get("runtime_run_id")
    attrs: Mapping[str, str] = ledger.attributes

    checks = (
        (release_ref, attrs.get("release_ref"), "release_ref mismatch"),
        (runtime_run_id, attrs.get("runtime_run_id"), "runtime_run_id mismatch"),
        (digest, attrs.get("evidence_digest"), "evidence_digest mismatch"),
    )
    for expected, actual, reason in checks:
        if expected != actual:
            return ProvenanceCheck(
                False,
                str(release_ref) if release_ref is not None else None,
                str(runtime_run_id) if runtime_run_id is not None else None,
                digest,
                reason,
            )

    return ProvenanceCheck(
        True,
        str(release_ref) if release_ref is not None else None,
        str(runtime_run_id) if runtime_run_id is not None else None,
        digest,
    )
