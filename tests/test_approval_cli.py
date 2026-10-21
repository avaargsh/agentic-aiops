import json

import pytest

from agentic_aiops import approval_cli


class FakeRuntime:
    def __init__(self, *, terminal: bool = False) -> None:
        self.terminal = terminal
        self.reference_ids: list[str] = []
        self.status_calls: list[object] = []
        self.resolution: dict[str, object] | None = None

    def start_or_attach(self, **kwargs: object) -> object:
        raise AssertionError("approval must not start or attach a workflow")

    def reference(self, *, runtime_run_id: str) -> object:
        self.reference_ids.append(runtime_run_id)
        return object()

    def status(self, run: object) -> dict[str, object]:
        self.status_calls.append(run)
        return {
            "phase": "paused" if not self.terminal else "succeeded",
            "paused": not self.terminal,
            "terminal": self.terminal,
            "evidence_refs": [],
        }

    def resolve_approval(
        self,
        run: object,
        *,
        approval_id: str,
        approved: bool,
        evidence_refs: tuple[str, ...] = (),
        reason: str | None = None,
    ) -> None:
        self.resolution = {
            "run": run,
            "approval_id": approval_id,
            "approved": approved,
            "evidence_refs": evidence_refs,
            "reason": reason,
        }


@pytest.mark.parametrize(("decision", "approved"), [("approve", True), ("deny", False)])
def test_approval_cli_references_existing_run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    decision: str,
    approved: bool,
) -> None:
    runtime = FakeRuntime()
    monkeypatch.setattr(approval_cli, "build_temporal_port", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "golden-approval",
            decision,
            "--run-id",
            "golden-ci-123",
            "--approval-id",
            "approval-123",
            "--reason",
            "operator decision",
            "--evidence-ref",
            "evidence://sha256/abc",
        ],
    )

    approval_cli.main()

    assert runtime.reference_ids == ["golden-ci-123"]
    assert len(runtime.status_calls) == 2
    assert runtime.resolution is not None
    assert runtime.resolution["approval_id"] == "approval-123"
    assert runtime.resolution["approved"] is approved
    assert runtime.resolution["evidence_refs"] == ("evidence://sha256/abc",)
    assert runtime.resolution["reason"] == "operator decision"

    output = json.loads(capsys.readouterr().out)
    assert output["run_id"] == "golden-ci-123"
    assert output["approval_id"] == "approval-123"
    assert output["decision"] == decision


def test_approval_cli_refuses_terminal_run_without_signaling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeRuntime(terminal=True)
    monkeypatch.setattr(approval_cli, "build_temporal_port", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "golden-approval",
            "approve",
            "--run-id",
            "already-complete",
            "--approval-id",
            "approval-123",
        ],
    )

    with pytest.raises(SystemExit, match="already terminal"):
        approval_cli.main()

    assert runtime.reference_ids == ["already-complete"]
    assert runtime.resolution is None
