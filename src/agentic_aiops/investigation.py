from __future__ import annotations

from .models import Evidence, Hypothesis, Incident, VerificationStatus


class Investigation:
    def __init__(self, incident: Incident) -> None:
        self.incident = incident
        self.evidence: dict[str, Evidence] = {}
        self.hypotheses: dict[str, Hypothesis] = {}

    def add_evidence(self, item: Evidence) -> None:
        if item.evidence_id in self.evidence:
            raise ValueError(f"duplicate evidence id: {item.evidence_id}")
        self.evidence[item.evidence_id] = item

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        if hypothesis.hypothesis_id in self.hypotheses:
            raise ValueError(f"duplicate hypothesis id: {hypothesis.hypothesis_id}")
        self.hypotheses[hypothesis.hypothesis_id] = hypothesis

    def verify(
        self,
        hypothesis_id: str,
        *,
        status: VerificationStatus,
        evidence_ids: list[str],
    ) -> Hypothesis:
        missing = [eid for eid in evidence_ids if eid not in self.evidence]
        if missing:
            raise ValueError(f"unknown evidence ids: {missing}")

        hypothesis = self.hypotheses[hypothesis_id]
        hypothesis.status = status
        hypothesis.evidence_ids = list(evidence_ids)
        return hypothesis
