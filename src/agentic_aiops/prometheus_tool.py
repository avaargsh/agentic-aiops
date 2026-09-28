from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence
from urllib.parse import urlencode
from uuid import uuid4

from .http_client import JsonHttpClient
from .models import Evidence, Incident


@dataclass(frozen=True)
class PrometheusQuery:
    name: str
    promql: str


@dataclass
class PrometheusReadTool:
    base_url: str
    queries: Sequence[PrometheusQuery]
    client: JsonHttpClient = JsonHttpClient()
    name: str = "prometheus"

    def collect(
        self,
        incident: Incident,
    ) -> Sequence[Evidence]:
        evidence: list[Evidence] = []

        for query in self.queries:
            url = (
                self.base_url.rstrip("/")
                + "/api/v1/query?"
                + urlencode({"query": query.promql})
            )
            payload = self.client.get_json(url)

            if payload.get("status") != "success":
                raise RuntimeError(
                    f"Prometheus query failed: {query.name}"
                )

            data = dict(payload.get("data") or {})
            result = list(data.get("result") or [])

            evidence.append(
                Evidence(
                    evidence_id=str(uuid4()),
                    source="prometheus",
                    observation=(
                        f"{query.name}: "
                        f"{len(result)} series returned"
                    ),
                    attributes={
                        "tool": self.name,
                        "query_name": query.name,
                        "promql": query.promql,
                        "result_type": str(
                            data.get("resultType", "")
                        ),
                        "result_json": json.dumps(
                            result,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        "incident_id": (
                            incident.incident_id
                        ),
                    },
                )
            )

        return evidence
