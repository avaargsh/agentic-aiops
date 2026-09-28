from agentic_aiops.bundle import EvidenceBundle
from agentic_aiops.models import (
    Evidence,
    Hypothesis,
    Incident,
    VerificationStatus,
)
from agentic_aiops.report import render_rca_markdown


def test_report_preserves_verification_status() -> None:
    bundle = EvidenceBundle(
        incident=Incident("inc-1", "latency", "sev2"),
        evidence=[
            Evidence("e-1", "prometheus", "db pool 98%"),
        ],
        hypotheses=[
            Hypothesis(
                "h-1",
                "database saturation",
                ["e-1"],
                VerificationStatus.SUPPORTED,
            )
        ],
    )

    report = render_rca_markdown(bundle)

    assert "SUPPORTED" in report
    assert "database saturation" in report
    assert "e-1" in report
