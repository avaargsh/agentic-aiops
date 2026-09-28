# Golden Incident v0.1 recording path

The control path is intentionally split at durable approval. No AIOps process polls while waiting.

```bash
# 1. Start: collect evidence, decide, pause Temporal Run
python examples/live_golden_incident.py start --run-id golden-checkout-live-001

# 2. Inspect durable state
python examples/live_golden_incident.py status --run-id golden-checkout-live-001

# 3. Operator approval: stable approval_id, Temporal owns dedupe
golden-approval approve --run-id golden-checkout-live-001 --approval-id approval-001 --reason "scale checkout-api"

# 4. Continue: approved state is required before any Kubernetes write
python examples/live_golden_incident.py continue --run-id golden-checkout-live-001

# 5. Inspect terminal state + evidence refs
python examples/live_golden_incident.py status --run-id golden-checkout-live-001
```

Expected lifecycle:

```text
Observe -> Evidence -> Decide -> WAIT_APPROVAL
                         -> approval_resolved
                         -> resume
                         -> scale 2 -> 4
                         -> Prometheus verify
                         -> COMPLETE + evidence refs
```

A denial uses the same command boundary:

```bash
golden-approval deny --run-id golden-checkout-live-001 --approval-id approval-001 --reason "change rejected"
```

The Temporal workflow is the idempotency owner for `approval_id`; clients preserve the stable ID and may safely retry signal delivery.
