import pytest

from agentic_aiops import (
    ActionPolicy,
    Evidence,
    Hypothesis,
    Incident,
    Investigation,
    VerificationStatus,
)


def test_hypothesis_requires_known_evidence() -> None:
    inv = Investigation(Incident("inc-1", "API latency", "sev2"))
    inv.add_hypothesis(Hypothesis("h-1", "database saturation"))

    with pytest.raises(ValueError):
        inv.verify(
            "h-1",
            status=VerificationStatus.SUPPORTED,
            evidence_ids=["missing"],
        )


def test_verified_hypothesis_links_evidence() -> None:
    inv = Investigation(Incident("inc-1", "API latency", "sev2"))
    inv.add_evidence(Evidence("e-1", "prometheus", "db cpu > 90%"))
    inv.add_hypothesis(Hypothesis("h-1", "database saturation"))

    result = inv.verify(
        "h-1",
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["e-1"],
    )

    assert result.status == VerificationStatus.SUPPORTED
    assert result.evidence_ids == ["e-1"]


def test_action_policy_requires_approval_for_write() -> None:
    result = ActionPolicy().evaluate(
        action_kind="restart",
        blast_radius="single-workload",
        rollback_available=True,
    )
    assert result.allowed is True
    assert result.requires_approval is True
