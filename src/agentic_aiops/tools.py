from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence
from uuid import uuid4

from .models import Evidence, Incident


class ReadTool(Protocol):
    name: str

    def collect(self, incident: Incident) -> Sequence[Evidence]:
        ...


@dataclass
class StaticReadTool:
    name: str
    observations: list[str]
    source: str = "static"

    def collect(self, incident: Incident) -> Sequence[Evidence]:
        return [
            Evidence(
                evidence_id=str(uuid4()),
                source=self.source,
                observation=observation,
                attributes={
                    "tool": self.name,
                    "incident_id": incident.incident_id,
                },
            )
            for observation in self.observations
        ]
