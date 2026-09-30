from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .action_orchestrator import OrchestratedAction
from .remediation import RemediationResult


def action_key(*, runtime_run_id: str, action: OrchestratedAction) -> str:
    payload = {
        "runtime_run_id": runtime_run_id,
        "decision_id": action.decision_id or "",
        "action_kind": action.proposal.action_kind,
        "target": action.proposal.target,
        "evidence_digest": action.ledger.attributes.get("evidence_digest", ""),
        "authority_digest": action.ledger.attributes.get("authority_digest", ""),
        "approval_id": action.ledger.attributes.get("approval_id", ""),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def receipt_path(run_dir: Path, key: str) -> Path:
    return run_dir / "actions" / f"{key}.json"


def load_receipt(run_dir: Path, key: str) -> RemediationResult | None:
    path = receipt_path(run_dir, key)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    from .remediation import ExecutionResult, VerificationResult, RollbackResult
    return RemediationResult(
        status=data["status"],
        execution=ExecutionResult(**data["execution"]) if data.get("execution") else None,
        verification=VerificationResult(**data["verification"]) if data.get("verification") else None,
        rollback=RollbackResult(**data["rollback"]) if data.get("rollback") else None,
        evidence_ids=tuple(data.get("evidence_ids", ())),
    )


def store_receipt(run_dir: Path, key: str, result: RemediationResult) -> Path:
    path = receipt_path(run_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False), encoding="utf-8")
    return path
