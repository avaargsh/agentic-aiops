from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .bundle import EvidenceBundle
from .investigation import Investigation
from .models import Hypothesis, Incident, VerificationStatus
from .tools import ReadTool


HypothesisFn = Callable[[Investigation], Sequence[Hypothesis]]


@dataclass(frozen=True)
class InvestigationResult:
    bundle: EvidenceBundle
    supported_hypotheses: tuple[Hypothesis, ...]


class InvestigationRunner:
    """Read-only evidence collection followed by explicit hypothesis verification."""

    def __init__(
        self,
        *,
        tools: Sequence[ReadTool],
        hypothesis_fn: HypothesisFn,
    ) -> None:
        self.tools = list(tools)
        self.hypothesis_fn = hypothesis_fn

    def run(self, incident: Incident) -> InvestigationResult:
        investigation = Investigation(incident)

        for tool in self.tools:
            for evidence in tool.collect(incident):
                investigation.add_evidence(evidence)

        proposed = list(self.hypothesis_fn(investigation))
        for hypothesis in proposed:
            investigation.add_hypothesis(hypothesis)

        supported = tuple(
            hypothesis
            for hypothesis in investigation.hypotheses.values()
            if hypothesis.status == VerificationStatus.SUPPORTED
        )

        bundle = EvidenceBundle(
            incident=incident,
            evidence=list(investigation.evidence.values()),
            hypotheses=list(investigation.hypotheses.values()),
            metadata={
                "tool_count": len(self.tools),
                "evidence_count": len(investigation.evidence),
            },
        )

        return InvestigationResult(
            bundle=bundle,
            supported_hypotheses=supported,
        )
