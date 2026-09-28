from agentic_aiops.alertmanager import incident_from_alertmanager


def test_alertmanager_payload_maps_to_incident() -> None:
    incident = incident_from_alertmanager(
        {
            "groupKey": "group-1",
            "status": "firing",
            "commonLabels": {
                "severity": "sev2",
                "cluster": "prod-a",
                "namespace": "checkout",
                "service": "api",
            },
            "commonAnnotations": {
                "summary": "checkout p99 latency high",
            },
        }
    )

    assert incident.incident_id == "group-1"
    assert incident.severity == "sev2"
    assert incident.summary == "checkout p99 latency high"
    assert "cluster=prod-a" in incident.scope
