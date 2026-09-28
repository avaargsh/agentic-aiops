from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

@dataclass
class AsyncTemporalPortAdapter:
    """Adapter contract for cloud-agent-runtime TemporalRunBridge.

    Callers provide a sync runner because agentic-aiops keeps its core synchronous.
    Production services can replace this with an async orchestration shell later.
    """

    bridge: Any
    run_async: Callable[[Awaitable[Any]], Any]

    def start_or_attach(self, *, runtime_run_id: str, session_id: str) -> Any:
        return self.run_async(self.bridge.start_or_attach(runtime_run_id=runtime_run_id, session_id=session_id))

    def pause(self, run: Any, *, evidence_refs: Sequence[str]) -> None:
        self.run_async(self.bridge.driver.signal(run, name="pause_run", payload={"evidence_refs": list(evidence_refs)}))

    def status(self, run: Any) -> dict[str, Any]:
        status = self.run_async(self.bridge.get_run_status(run))
        raw = self.run_async(self.bridge.driver.query(run, name="run_state"))
        return {**dict(raw), "phase": status.phase, "paused": status.paused, "terminal": status.terminal, "evidence_refs": list(status.evidence_refs)}

    def resolve_approval(self, run: Any, *, approval_id: str, approved: bool, evidence_refs: Sequence[str] = (), reason: str | None = None) -> None:
        self.run_async(self.bridge.signal_approval(run, approval_id=approval_id, approved=approved, evidence_refs=evidence_refs, reason=reason))
        if approved:
            self.run_async(self.bridge.driver.signal(run, name="resume_run", payload={"approval_id": approval_id}))

    def complete(self, run: Any, *, result: dict[str, Any], evidence_refs: Sequence[str]) -> None:
        self.run_async(self.bridge.complete(run, result=result, evidence_refs=evidence_refs))
