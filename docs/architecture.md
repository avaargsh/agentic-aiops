# Architecture

## Principle: evidence before explanation

AIOps becomes dangerous when a fluent RCA is treated as evidence.

The system therefore separates:

1. **observation** — raw or normalized facts,
2. **hypothesis** — a proposed explanation,
3. **verification** — evidence that supports or rejects it,
4. **decision** — what to do next,
5. **authorization** — whether the action may execute,
6. **post-action verification** — whether the action worked.

## Control loop

```text
Alert / SLO Burn
      |
Normalize + Scope
      |
Topology / Change Context
      |
Planner
      |
Read-only Investigation Tools
      |
Evidence Graph
      |
Hypothesis Set
      |
Verifier
      |
RCA / Decision
      |
Deterministic Action Policy
   /             \
Advisory       Approval
                  |
             Safe Executor
                  |
             Verify Outcome
                  |
                Replay
```

## Evidence graph

Evidence is first-class data, not prose embedded in a model answer.

Each item should be able to retain:

- source,
- observation,
- time,
- entity/scope,
- query/tool reference,
- trace/log/metric pointer.

Hypotheses link to evidence IDs.

## Action boundary

The learned system may recommend an action. A deterministic gate still owns:

- authorization,
- blast radius,
- approval,
- budget,
- rollback requirement,
- protected resources.

## Durable workflows

Long investigations need durable execution. Temporal or an equivalent workflow engine can own:

- retry,
- timeouts,
- approval waits,
- long-running verification,
- replayable control state.

The model should not be the workflow engine.
