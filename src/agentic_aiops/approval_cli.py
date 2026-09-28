from __future__ import annotations

import argparse
import json

from .temporal_factory import build_temporal_port

def main() -> None:
    parser = argparse.ArgumentParser(prog="golden-approval")
    parser.add_argument("decision", choices=["approve", "deny"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--session-id", default="golden-demo")
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--reason")
    parser.add_argument("--evidence-ref", action="append", default=[])
    args = parser.parse_args()

    runtime = build_temporal_port()
    run = runtime.start_or_attach(runtime_run_id=args.run_id, session_id=args.session_id)
    before = runtime.status(run)
    if before.get("terminal"):
        raise SystemExit(f"run {args.run_id} is already terminal")

    runtime.resolve_approval(
        run,
        approval_id=args.approval_id,
        approved=args.decision == "approve",
        evidence_refs=tuple(args.evidence_ref),
        reason=args.reason,
    )
    after = runtime.status(run)
    print(json.dumps({"run_id": args.run_id, "approval_id": args.approval_id, "decision": args.decision, "phase": after.get("phase"), "paused": after.get("paused"), "terminal": after.get("terminal"), "evidence_refs": after.get("evidence_refs", [])}, indent=2))

if __name__ == "__main__":
    main()
