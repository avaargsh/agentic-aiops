from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

class DurableRunPort(Protocol):
    def start_or_attach(self, *, runtime_run_id: str, session_id: str) -> Any: ...
    def pause(self, run: Any, *, evidence_refs: Sequence[str]) -> None: ...
    def status(self, run: Any) -> dict[str, Any]: ...
    def complete(self, run: Any, *, result: dict[str, Any], evidence_refs: Sequence[str]) -> None: ...

@dataclass(frozen=True)
class DurableRunContext:
    runtime_run_id: str
    session_id: str
    release_ref: str | None = None
    authority_digest: str | None = None
    evidence_uri_prefix: str = "evidence://sha256"
    artifact_root: str | Path = ".golden-runs"

    def bundle_ref(self, bundle_sha256: str) -> str:
        return f"{self.evidence_uri_prefix}/{bundle_sha256}"

    @property
    def run_dir(self) -> Path:
        return Path(self.artifact_root) / self.runtime_run_id
