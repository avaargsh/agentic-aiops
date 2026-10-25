import math

import pytest

from agentic_aiops.sre_recommendation import validate_sre_recommendation


def payload(**overrides):
    value = {
        "schema_version": "sre-decision/v1",
        "change_id": "change-123",
        "action": "canary",
        "reason_code": "MINIMUM_EXPECTED_LOSS_UNDER_CONSTRAINTS",
        "expected_losses": {
            "allow": 10.0,
            "canary": 2.0,
            "human_review": 3.0,
            "reject": 15.0,
        },
        "excluded_actions": {},
        "risk_context_multiplier": 1.4,
        "evidence_ids": ["diff:change-123", "slo:checkout"],
        "model_id": "risk-model@sha256:abc",
        "calibration_id": "calibration@sha256:def",
        "policy_version": "sre-policy-v1",
        "authorized": False,
    }
    value.update(overrides)
    return value


def validate(value=None, **kwargs):
    return validate_sre_recommendation(
        payload() if value is None else value,
        expected_change_id="change-123",
        available_evidence_ids=("diff:change-123", "slo:checkout", "incident:current"),
        **kwargs,
    )


def test_valid_recommendation_is_typed_and_never_authorizes_execution():
    result = validate()
    assert result.change_id == "change-123"
    assert result.action == "canary"
    assert result.expected_losses["canary"] == pytest.approx(2.0)
    assert result.authorized is False
    assert result.to_dict()["authorized"] is False


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": "sre-decision/v2"}, "schema_version"),
        ({"change_id": "change-other"}, "change_id"),
        ({"authorized": True}, "must be false"),
        ({"action": "execute"}, "action"),
        ({"unexpected": "field"}, "fields mismatch"),
        ({"evidence_ids": ["diff:change-123", "unknown:evidence"]}, "not present"),
        ({"evidence_ids": []}, "non-empty"),
        ({"evidence_ids": ["diff:change-123", "diff:change-123"]}, "unique"),
        ({"expected_losses": {"canary": math.nan}}, "finite non-negative"),
        ({"expected_losses": {"canary": -1}}, "finite non-negative"),
        (
            {"expected_losses": {"canary": 2.0}, "excluded_actions": {}},
            "every action must have an expected loss or an exclusion reason",
        ),
        ({"action": "canary", "expected_losses": {"allow": 1.0}}, "selected action must have expected loss"),
        ({"action": "canary", "expected_losses": {"canary": 2.0}, "excluded_actions": {"canary": "blocked"}}, "cannot be excluded"),
        ({"risk_context_multiplier": 0.5}, "risk_context_multiplier"),
        ({"model_id": ""}, "model_id"),
        ({"policy_version": ""}, "policy_version"),
    ],
)
def test_invalid_or_cross_change_recommendation_fails_closed(changes, message):
    with pytest.raises(ValueError, match=message):
        validate(payload(**changes))


def test_human_review_can_be_a_proper_abstention_without_expected_loss_values():
    result = validate(
        payload(
            action="human_review",
            reason_code="UNCERTAINTY_REQUIRES_HUMAN_REVIEW",
            expected_losses={},
            excluded_actions={
                "allow": "UNCERTAINTY_REQUIRES_HUMAN_REVIEW",
                "canary": "UNCERTAINTY_REQUIRES_HUMAN_REVIEW",
                "reject": "UNCERTAINTY_REQUIRES_HUMAN_REVIEW",
            },
            risk_context_multiplier=None,
            model_id=None,
            calibration_id=None,
        )
    )
    assert result.action == "human_review"
    assert result.expected_losses == {}
    assert result.authorized is False


def test_recommendation_rejects_when_current_evidence_set_is_empty():
    with pytest.raises(ValueError, match="available_evidence_ids"):
        validate_sre_recommendation(
            payload(),
            expected_change_id="change-123",
            available_evidence_ids=(),
        )


def test_recommendation_must_not_mark_a_scored_action_as_excluded():
    candidate = payload(
        action="reject",
        expected_losses={"reject": 15.0},
        excluded_actions={
            "allow": "blocked",
            "canary": "blocked",
            "human_review": "blocked",
        },
    )
    result = validate(candidate)
    assert result.action == "reject"


@pytest.mark.parametrize(
    "changes",
    [
        {"model_id": None},
        {"calibration_id": None},
        {"risk_context_multiplier": None},
    ],
)
def test_scored_recommendation_requires_model_calibration_and_context_provenance(changes):
    with pytest.raises(ValueError, match="scored recommendation requires"):
        validate(payload(**changes))
