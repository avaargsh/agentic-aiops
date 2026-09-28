# Replay Metrics to Release Gate

AIOps replay output is converted into a small numeric metric map.

Example:

```json
{
  "unsupported_claim_rate": 0.01,
  "false_automation_rate": 0.0,
  "escalation_accuracy": 0.96,
  "unnecessary_tool_rate": 0.08,
  "recovery_success_rate": 0.94
}
```

The names intentionally match metrics that can be consumed directly by the Agent Control Plane EvalGate.

This keeps responsibilities separate:

```text
agentic-aiops
  = replay and measure behavior

agent-control-plane
  = decide whether a Release is promotable
```

No AIOps evaluator promotes a release by itself.
