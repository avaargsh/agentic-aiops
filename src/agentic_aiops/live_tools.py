from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from uuid import uuid4

from .models import Evidence, Incident


def _ssl_context(
    *,
    verify_tls: bool,
    ca_file: str | None,
) -> ssl.SSLContext:
    if verify_tls:
        return ssl.create_default_context(
            cafile=ca_file,
        )
    return ssl._create_unverified_context()


@dataclass
class PrometheusReadTool:
    base_url: str
    queries: dict[str, str]
    bearer_token: str | None = None
    timeout_seconds: float = 5.0
    verify_tls: bool = True
    ca_file: str | None = None
    name: str = "prometheus"

    def _get_json(self, path: str) -> dict[str, Any]:
        headers = {"accept": "application/json"}
        if self.bearer_token:
            headers["authorization"] = (
                f"Bearer {self.bearer_token}"
            )

        req = request.Request(
            self.base_url.rstrip("/") + path,
            headers=headers,
            method="GET",
        )
        with request.urlopen(
            req,
            timeout=self.timeout_seconds,
            context=_ssl_context(
                verify_tls=self.verify_tls,
                ca_file=self.ca_file,
            ),
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    def collect(
        self,
        incident: Incident,
    ) -> list[Evidence]:
        evidence: list[Evidence] = []

        for label, query_text in self.queries.items():
            query_string = parse.urlencode(
                {"query": query_text}
            )
            payload = self._get_json(
                "/api/v1/query?" + query_string
            )
            if payload.get("status") != "success":
                raise RuntimeError(
                    f"Prometheus query failed: {label}"
                )

            result = (
                payload.get("data", {})
                .get("result", [])
            )
            evidence.append(
                Evidence(
                    evidence_id=str(uuid4()),
                    source="prometheus",
                    observation=(
                        f"{label}: "
                        f"{len(result)} series returned"
                    ),
                    attributes={
                        "tool": self.name,
                        "incident_id": (
                            incident.incident_id
                        ),
                        "query_label": label,
                        "query": query_text,
                        "result": result,
                    },
                )
            )

        return evidence


@dataclass
class KubernetesReadTool:
    api_server: str
    paths: dict[str, str]
    bearer_token: str | None = None
    timeout_seconds: float = 5.0
    verify_tls: bool = True
    ca_file: str | None = None
    name: str = "kubernetes"

    def _get_json(self, path: str) -> dict[str, Any]:
        headers = {"accept": "application/json"}
        if self.bearer_token:
            headers["authorization"] = (
                f"Bearer {self.bearer_token}"
            )

        req = request.Request(
            self.api_server.rstrip("/")
            + "/"
            + path.lstrip("/"),
            headers=headers,
            method="GET",
        )
        with request.urlopen(
            req,
            timeout=self.timeout_seconds,
            context=_ssl_context(
                verify_tls=self.verify_tls,
                ca_file=self.ca_file,
            ),
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    def collect(
        self,
        incident: Incident,
    ) -> list[Evidence]:
        evidence: list[Evidence] = []

        for label, path in self.paths.items():
            payload = self._get_json(path)
            items = payload.get("items")
            count = (
                len(items)
                if isinstance(items, list)
                else 1
            )

            evidence.append(
                Evidence(
                    evidence_id=str(uuid4()),
                    source="kubernetes",
                    observation=(
                        f"{label}: {count} object(s) returned"
                    ),
                    attributes={
                        "tool": self.name,
                        "incident_id": (
                            incident.incident_id
                        ),
                        "resource_label": label,
                        "path": path,
                        "response": payload,
                    },
                )
            )

        return evidence
