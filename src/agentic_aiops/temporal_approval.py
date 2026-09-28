from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .durable_runtime import DurableRunContext, DurableRunPort
from .golden_incident import GoldenIncidentResult, GoldenIncidentRunner
from .models import Incident

@dataclass
class TemporalApprovalRunner:
    runner: GoldenIncidentRunner
    runtime: DurableRunPort
    poll_seconds: float = 1.0
    timeout_seconds: float = 300.0

    def run(self, incident: Incident, *, context: DurableRunContext) -> GoldenIncidentResult:
        first = self.runner.run_durable(incident, runtime=self.runtime, context=context)
        if first is not None:
            return first
        run = self.runtime.start_or_attach(runtime_run_id=context.runtime_run_id, session_id=context.session_id)
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            state = self.runtime.status(run)
            events = list(state.get("approval_events") or [])
            if any(event.get("approved") is False for event in events):
                raise RuntimeError("approval denied")
            if any(event.get("approved") is True for event in events):
                resumed = self.runner.run_durable(incident, runtime=self.runtime, context=context)
                if resumed is None:
                    raise RuntimeError("approved run did not resume")
                return resumed
            time.sleep(self.poll_seconds)
        raise TimeoutError(f"approval timed out for {context.runtime_run_id}")
