from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .models import (
    ChangeEvent,
    Evidence,
    Hypothesis,
    Incident,
    TopologyEdge,
    TopologyEntity,
    VerificationStatus,
)


@dataclass
class EvidenceBundle:
    incident: Incident
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    entities: list[TopologyEntity] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)
    changes: list[ChangeEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident": asdict(self.incident),
            "evidence": [asdict(item) for item in self.evidence],
            "hypotheses": [
                {
                    **asdict(item),
                    "status": item.status.value,
                }
                for item in self.hypotheses
            ],
            "entities": [asdict(item) for item in self.entities],
            "edges": [asdict(item) for item in self.edges],
            "changes": [asdict(item) for item in self.changes],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceBundle":
        return cls(
            incident=Incident(**data["incident"]),
            evidence=[
                Evidence(
                    **{
                        **item,
                        "entity_refs": tuple(item.get("entity_refs", ())),
                    }
                )
                for item in data.get("evidence", [])
            ],
            hypotheses=[
                Hypothesis(
                    hypothesis_id=item["hypothesis_id"],
                    statement=item["statement"],
                    evidence_ids=list(item.get("evidence_ids", [])),
                    status=VerificationStatus(
                        item.get("status", VerificationStatus.UNVERIFIED.value)
                    ),
                )
                for item in data.get("hypotheses", [])
            ],
            entities=[
                TopologyEntity(**item)
                for item in data.get("entities", [])
            ],
            edges=[
                TopologyEdge(**item)
                for item in data.get("edges", [])
            ],
            changes=[
                ChangeEvent(**item)
                for item in data.get("changes", [])
            ],
            metadata=dict(data.get("metadata", {})),
        )

    def canonical_json(self) -> str:
        payload = self.to_dict()
        payload["metadata"] = {
            key: value
            for key, value in payload.get("metadata", {}).items()
            if key != "bundle_sha256"
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                self.to_dict(),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    @classmethod
    def read_json(cls, path: str | Path) -> "EvidenceBundle":
        return cls.from_dict(
            json.loads(Path(path).read_text(encoding="utf-8"))
        )
