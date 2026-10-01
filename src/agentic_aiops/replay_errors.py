from __future__ import annotations

from enum import StrEnum


class ReplayErrorCode(StrEnum):
    FROZEN_STATE_MISSING = "FROZEN_STATE_MISSING"
    RELEASE_MISMATCH = "RELEASE_MISMATCH"
    RUN_MISMATCH = "RUN_MISMATCH"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"
    RECEIPT_MISSING = "RECEIPT_MISSING"
    OPERATION_MISSING = "OPERATION_MISSING"
    OPERATION_NOT_TERMINAL = "OPERATION_NOT_TERMINAL"
    RESULT_MISSING = "RESULT_MISSING"
    RECEIPT_MISMATCH = "RECEIPT_MISMATCH"
    DECISION_MISMATCH = "DECISION_MISMATCH"
    APPROVAL_MISMATCH = "APPROVAL_MISMATCH"


class ReplayValidationError(RuntimeError):
    """Stable fail-closed replay error for callers and observability."""

    def __init__(self, code: ReplayErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)
