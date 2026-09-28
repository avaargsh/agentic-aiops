from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .action_orchestrator import OrchestratedAction, ProposedAction


@dataclass(frozen=True)
class ExecutionResult:
    changed: bool
    resource_ref: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    evidence_ids: tuple[str, ...] = ()
    summary: str | None = None


@dataclass(frozen=True)
class RollbackResult:
    rolled_back: bool
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RemediationResult:
    status: str
    execution: ExecutionResult | None
    verification: VerificationResult | None
    rollback: RollbackResult | None
    evidence_ids: tuple[str, ...]


class ActionExecutor(Protocol):
    def execute(
        self,
        action: ProposedAction,
    ) -> ExecutionResult:
        ...

    def rollback(
        self,
        action: ProposedAction,
        execution: ExecutionResult,
    ) -> RollbackResult:
        ...


class PostActionVerifier(Protocol):
    def verify(
        self,
        action: ProposedAction,
        execution: ExecutionResult,
    ) -> VerificationResult:
        ...


class SafeRemediationRunner:
    """Execute only authorized/approved actions and verify the outcome."""

    def __init__(
        self,
        *,
        executor: ActionExecutor,
        verifier: PostActionVerifier,
    ) -> None:
        self.executor = executor
        self.verifier = verifier

    def run(
        self,
        orchestrated: OrchestratedAction,
        *,
        approval_granted: bool = False,
    ) -> RemediationResult:
        if orchestrated.selected_path != "execute":
            return RemediationResult(
                status="NOT_SELECTED_FOR_EXECUTION",
                execution=None,
                verification=None,
                rollback=None,
                evidence_ids=orchestrated.proposal.evidence_ids,
            )

        authorized = orchestrated.execution_allowed or (
            orchestrated.approval_required
            and approval_granted
            and orchestrated.policy.allowed
        )

        if not authorized:
            return RemediationResult(
                status="NOT_AUTHORIZED",
                execution=None,
                verification=None,
                rollback=None,
                evidence_ids=orchestrated.proposal.evidence_ids,
            )

        execution = self.executor.execute(
            orchestrated.proposal
        )
        verification = self.verifier.verify(
            orchestrated.proposal,
            execution,
        )

        all_evidence = list(
            orchestrated.proposal.evidence_ids
        )
        all_evidence.extend(execution.evidence_ids)
        all_evidence.extend(verification.evidence_ids)

        if verification.passed:
            return RemediationResult(
                status="VERIFIED",
                execution=execution,
                verification=verification,
                rollback=None,
                evidence_ids=tuple(
                    dict.fromkeys(all_evidence)
                ),
            )

        rollback = None
        if (
            orchestrated.proposal.rollback_available
            and execution.changed
        ):
            rollback = self.executor.rollback(
                orchestrated.proposal,
                execution,
            )
            all_evidence.extend(rollback.evidence_ids)

        return RemediationResult(
            status=(
                "ROLLED_BACK"
                if rollback is not None
                and rollback.rolled_back
                else "VERIFICATION_FAILED"
            ),
            execution=execution,
            verification=verification,
            rollback=rollback,
            evidence_ids=tuple(
                dict.fromkeys(all_evidence)
            ),
        )
