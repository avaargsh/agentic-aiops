"""Strict validator for SRE recommendations before they enter AIOps workflows.

Acceptance validates provenance and structure only. It never grants permission
to execute an action; deterministic policy and the control plane remain in charge.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

SCHEMA_VERSION = "sre-decision/v1"
ACTIONS = frozenset({"allow", "canary", "human_review", "reject"})
_FIELDS = frozenset(
    {
        "schema_version",
        "change_id",
        "action",
        "reason_code",
        "expected_losses",
        "excluded_actions",
        "risk_context_multiplier",
        "evidence_ids",
        "model_id",
        "calibration_id",
        "policy_version",
        "authorized",
    }
)


def _nonempty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _finite_nonnegative(value: object, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} values must be finite non-negative numbers")
    return float(value)


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be an array of unique non-empty strings")
    result = tuple(_nonempty_string(item, name) for item in value)
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must contain unique values")
    return result


def _cost_mapping(value: object, name: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    result: dict[str, float] = {}
    for key, amount in value.items():
        action = _nonempty_string(key, f"{name} action")
        if action not in ACTIONS:
            raise ValueError(f"{name} contains unsupported action {action!r}")
        result[action] = _finite_nonnegative(amount, name)
    return result


def _reason_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("excluded_actions must be an object")
    result: dict[str, str] = {}
    for key, reason in value.items():
        action = _nonempty_string(key, "excluded_actions action")
        if action not in ACTIONS:
            raise ValueError(f"excluded_actions contains unsupported action {action!r}")
        result[action] = _nonempty_string(reason, f"excluded_actions[{action}]")
    return result


@dataclass(frozen=True)
class SREDecisionRecommendation:
    schema_version: str
    change_id: str
    action: str
    reason_code: str
    expected_losses: Mapping[str, float]
    excluded_actions: Mapping[str, str]
    risk_context_multiplier: float | None
    evidence_ids: tuple[str, ...]
    model_id: str | None
    calibration_id: str | None
    policy_version: str
    authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "expected_losses",
            MappingProxyType(dict(self.expected_losses)),
        )
        object.__setattr__(
            self,
            "excluded_actions",
            MappingProxyType(dict(self.excluded_actions)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "change_id": self.change_id,
            "action": self.action,
            "reason_code": self.reason_code,
            "expected_losses": dict(self.expected_losses),
            "excluded_actions": dict(self.excluded_actions),
            "risk_context_multiplier": self.risk_context_multiplier,
            "evidence_ids": list(self.evidence_ids),
            "model_id": self.model_id,
            "calibration_id": self.calibration_id,
            "policy_version": self.policy_version,
            "authorized": False,
        }


def validate_sre_recommendation(
    payload: Mapping[str, Any],
    *,
    expected_change_id: str,
    available_evidence_ids: Sequence[str],
) -> SREDecisionRecommendation:
    """Validate SRE recommendation identity, evidence scope, and non-authority.

    The expected change ID and evidence IDs must come from the caller's current
    proposal and frozen evidence bundle, never from the recommendation itself.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("SRE recommendation must be an object")
    if set(payload) != _FIELDS:
        missing = sorted(_FIELDS - set(payload))
        extra = sorted(set(payload) - _FIELDS)
        raise ValueError(f"SRE recommendation fields mismatch; missing={missing}, extra={extra}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    expected_change_id = _nonempty_string(expected_change_id, "expected_change_id")
    change_id = _nonempty_string(payload["change_id"], "change_id")
    if change_id != expected_change_id:
        raise ValueError("change_id does not match the active proposal")
    action = _nonempty_string(payload["action"], "action")
    if action not in ACTIONS:
        raise ValueError(f"unsupported action: {action}")
    reason_code = _nonempty_string(payload["reason_code"], "reason_code")
    policy_version = _nonempty_string(payload["policy_version"], "policy_version")

    authorized = payload["authorized"]
    if type(authorized) is not bool or authorized is not False:
        raise ValueError("authorized must be false; recommendations never grant execution authority")

    raw_losses = _cost_mapping(payload["expected_losses"], "expected_losses")
    raw_excluded = _reason_mapping(payload["excluded_actions"])
    if action != "human_review" and action not in raw_losses:
        raise ValueError("selected action must have expected loss unless it is human_review")
    if action in raw_excluded:
        raise ValueError("selected action cannot be excluded")
    overlap = set(raw_losses) & set(raw_excluded)
    if overlap:
        raise ValueError("an action cannot have both an expected loss and an exclusion reason")

    multiplier = payload["risk_context_multiplier"]
    if multiplier is not None:
        if type(multiplier) not in (int, float) or not math.isfinite(multiplier) or multiplier < 1:
            raise ValueError("risk_context_multiplier must be null or a finite number >= 1")
        multiplier = float(multiplier)

    evidence_ids = _string_tuple(payload["evidence_ids"], "evidence_ids")
    if not evidence_ids:
        raise ValueError("evidence_ids must be non-empty")
    available = _string_tuple(available_evidence_ids, "available_evidence_ids")
    if not available:
        raise ValueError("available_evidence_ids must be non-empty")
    unexpected = sorted(set(evidence_ids) - set(available))
    if unexpected:
        raise ValueError(
            "recommendation references evidence not present in the active bundle: "
            + ", ".join(unexpected)
        )

    model_id = payload["model_id"]
    calibration_id = payload["calibration_id"]
    if model_id is not None:
        model_id = _nonempty_string(model_id, "model_id")
    if calibration_id is not None:
        calibration_id = _nonempty_string(calibration_id, "calibration_id")

    return SREDecisionRecommendation(
        schema_version=SCHEMA_VERSION,
        change_id=change_id,
        action=action,
        reason_code=reason_code,
        expected_losses=raw_losses,
        excluded_actions=raw_excluded,
        risk_context_multiplier=multiplier,
        evidence_ids=evidence_ids,
        model_id=model_id,
        calibration_id=calibration_id,
        policy_version=policy_version,
        authorized=False,
    )
