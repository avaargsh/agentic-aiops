from __future__ import annotations

from .bundle import EvidenceBundle
from .investigation import Investigation


def investigation_from_bundle(bundle: EvidenceBundle) -> Investigation:
    investigation = Investigation(bundle.incident)

    for item in bundle.evidence:
        investigation.add_evidence(item)

    for hypothesis in bundle.hypotheses:
        investigation.add_hypothesis(hypothesis)

    return investigation
