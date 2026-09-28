from __future__ import annotations

from uuid import uuid4

from .models import Incident


def incident_from_alertmanager(payload: dict) -> Incident:
    common_labels = dict(payload.get("commonLabels", {}))
    common_annotations = dict(payload.get("commonAnnotations", {}))

    severity = str(
        common_labels.get("severity")
        or common_labels.get("priority")
        or "unknown"
    )
    summary = str(
        common_annotations.get("summary")
        or common_annotations.get("description")
        or payload.get("status")
        or "Alertmanager incident"
    )

    scope_parts = []
    for key in ("cluster", "namespace", "service", "pod", "node"):
        value = common_labels.get(key)
        if value:
            scope_parts.append(f"{key}={value}")

    return Incident(
        incident_id=str(payload.get("groupKey") or uuid4()),
        summary=summary,
        severity=severity,
        scope=",".join(scope_parts) if scope_parts else None,
    )
