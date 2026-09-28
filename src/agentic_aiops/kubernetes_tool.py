from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence
from uuid import uuid4

from .http_client import JsonHttpClient
from .models import Evidence, Incident


def parse_scope(
    scope: str | None,
) -> dict[str, str]:
    values: dict[str, str] = {}
    if not scope:
        return values

    for item in scope.split(","):
        key, separator, value = item.partition("=")
        if separator and key and value:
            values[key.strip()] = value.strip()

    return values


@dataclass
class KubernetesListTool:
    api_server: str
    resource_path_template: str
    client: JsonHttpClient = JsonHttpClient()
    name: str = "kubernetes"

    def collect(
        self,
        incident: Incident,
    ) -> Sequence[Evidence]:
        scope = parse_scope(incident.scope)

        try:
            resource_path = (
                self.resource_path_template.format(
                    **scope
                )
            )
        except KeyError as exc:
            raise ValueError(
                "incident scope missing Kubernetes "
                f"placeholder: {exc.args[0]}"
            ) from exc

        url = (
            self.api_server.rstrip("/")
            + "/"
            + resource_path.lstrip("/")
        )
        payload = self.client.get_json(url)

        items = list(payload.get("items") or [])
        names = [
            str(
                item.get("metadata", {}).get(
                    "name",
                    "",
                )
            )
            for item in items[:20]
        ]

        return [
            Evidence(
                evidence_id=str(uuid4()),
                source="kubernetes",
                observation=(
                    f"{resource_path}: "
                    f"{len(items)} objects returned"
                ),
                attributes={
                    "tool": self.name,
                    "resource_path": resource_path,
                    "object_names": json.dumps(
                        names,
                        ensure_ascii=False,
                    ),
                    "resource_version": str(
                        payload.get("metadata", {}).get(
                            "resourceVersion",
                            "",
                        )
                    ),
                    "incident_id": (
                        incident.incident_id
                    ),
                },
            )
        ]
