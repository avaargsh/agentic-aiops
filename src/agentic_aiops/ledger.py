from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class DecisionLedgerEntry:
    decision_type: str
    selected_action: str
    policy_reason: str
    evidence_ids: tuple[str, ...] = ()
    confidence: float | None = None
    requires_approval: bool = False
    outcome: str | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)
