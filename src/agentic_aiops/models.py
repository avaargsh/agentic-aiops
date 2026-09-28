from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    REJECTED = "rejected"


@dataclass(frozen=True)
class TopologyEntity:
    entity_id: str
    kind: str
    name: str
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TopologyEdge:
    source: str
    target: str
    relation: str


@dataclass(frozen=True)
class ChangeEvent:
    change_id: str
    entity_id: str
    kind: str
    summary: str
    timestamp: str | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source: str
    observation: str
    timestamp: str | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)
    entity_refs: tuple[str, ...] = ()


@dataclass
class Hypothesis:
    hypothesis_id: str
    statement: str
    evidence_ids: list[str] = field(default_factory=list)
    status: VerificationStatus = VerificationStatus.UNVERIFIED


@dataclass
class Incident:
    incident_id: str
    summary: str
    severity: str
    scope: str | None = None
