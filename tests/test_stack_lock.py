import json

import pytest

from agentic_aiops.stack_lock import StackLockError, github_outputs, load_stack_lock


def _valid_lock():
    return {
        "schema_version": 1,
        "baseline": "m1-stack",
        "dependencies": {
            "control_plane": {
                "repository": "avaargsh/agent-control-plane",
                "revision": "a" * 40,
            },
            "runtime": {
                "repository": "avaargsh/cloud-agent-runtime",
                "revision": "b" * 40,
            },
            "decision": {
                "repository": "avaargsh/agent-decision-lab",
                "revision": "c" * 40,
            },
        },
        "acceptance": {
            "success_gate": "PROMOTE",
            "negative_gate": "INVALID_RELEASE_EVIDENCE",
        },
    }


def test_load_stack_lock_and_resolve_outputs(tmp_path):
    path = tmp_path / "stack.lock.json"
    path.write_text(json.dumps(_valid_lock()), encoding="utf-8")

    data = load_stack_lock(path)

    assert github_outputs(data) == {
        "control_plane_ref": "a" * 40,
        "runtime_ref": "b" * 40,
        "decision_ref": "c" * 40,
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(schema_version=2), "schema_version"),
        (
            lambda d: d["dependencies"]["control_plane"].update(revision="main"),
            "full lowercase 40-char commit SHA",
        ),
        (
            lambda d: d["dependencies"]["runtime"].update(
                repository="example/cloud-agent-runtime"
            ),
            "runtime.repository",
        ),
        (
            lambda d: d["acceptance"].update(success_gate="ALLOW"),
            "acceptance.success_gate",
        ),
    ],
)
def test_invalid_stack_lock_fails_closed(tmp_path, mutate, message):
    data = _valid_lock()
    mutate(data)
    path = tmp_path / "stack.lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(StackLockError, match=message):
        load_stack_lock(path)
