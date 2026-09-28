from agentic_aiops import (
    Evidence,
    Hypothesis,
    Incident,
    Investigation,
    VerificationStatus,
)


inv = Investigation(
    Incident(
        incident_id="inc-demo",
        summary="checkout API p99 latency increased",
        severity="sev2",
        scope="namespace/checkout",
    )
)

inv.add_evidence(
    Evidence(
        evidence_id="e1",
        source="prometheus",
        observation="checkout CPU is normal; downstream DB pool saturation is high",
    )
)

inv.add_hypothesis(
    Hypothesis(
        hypothesis_id="h1",
        statement="downstream database connection pool saturation",
    )
)

print(
    inv.verify(
        "h1",
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["e1"],
    )
)
