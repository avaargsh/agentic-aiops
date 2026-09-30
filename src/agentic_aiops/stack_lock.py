from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

_REQUIRED = {
    "control_plane": "avaargsh/agent-control-plane",
    "runtime": "avaargsh/cloud-agent-runtime",
    "decision": "avaargsh/agent-decision-lab",
}

_OUTPUT_KEYS = {
    "control_plane": "control_plane_ref",
    "runtime": "runtime_ref",
    "decision": "decision_ref",
}


class StackLockError(ValueError):
    """Raised when stack.lock.json violates the public stack contract."""


def load_stack_lock(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_stack_lock(data)
    return data


def validate_stack_lock(data: dict[str, Any]) -> None:
    if data.get("schema_version") != 1:
        raise StackLockError("schema_version must be 1")

    dependencies = data.get("dependencies")
    if not isinstance(dependencies, dict):
        raise StackLockError("dependencies must be an object")

    missing = sorted(set(_REQUIRED) - set(dependencies))
    if missing:
        raise StackLockError(f"missing required dependencies: {', '.join(missing)}")

    for name, expected_repo in _REQUIRED.items():
        item = dependencies.get(name)
        if not isinstance(item, dict):
            raise StackLockError(f"{name} must be an object")

        repository = item.get("repository")
        if repository != expected_repo:
            raise StackLockError(
                f"{name}.repository must be {expected_repo!r}, got {repository!r}"
            )

        revision = item.get("revision")
        if not isinstance(revision, str) or not _SHA_RE.fullmatch(revision):
            raise StackLockError(f"{name}.revision must be a full lowercase 40-char commit SHA")

    acceptance = data.get("acceptance")
    if not isinstance(acceptance, dict):
        raise StackLockError("acceptance must be an object")
    if acceptance.get("success_gate") != "PROMOTE":
        raise StackLockError("acceptance.success_gate must remain PROMOTE")
    if acceptance.get("negative_gate") != "INVALID_RELEASE_EVIDENCE":
        raise StackLockError(
            "acceptance.negative_gate must remain INVALID_RELEASE_EVIDENCE"
        )


def github_outputs(data: dict[str, Any]) -> dict[str, str]:
    dependencies = data["dependencies"]
    return {
        output_key: dependencies[name]["revision"]
        for name, output_key in _OUTPUT_KEYS.items()
    }


def _write_github_output(path: Path, outputs: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and resolve the pinned cross-repository Agent stack."
    )
    parser.add_argument("path", nargs="?", default="stack.lock.json")
    parser.add_argument(
        "--github-output",
        type=Path,
        help="Append resolved dependency refs to a GitHub Actions output file.",
    )
    args = parser.parse_args(argv)

    data = load_stack_lock(args.path)
    outputs = github_outputs(data)

    if args.github_output is not None:
        _write_github_output(args.github_output, outputs)

    print(json.dumps({"baseline": data.get("baseline"), **outputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
