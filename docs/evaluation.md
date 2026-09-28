# Evaluation

Agentic AIOps must be evaluated on more than RCA text quality.

## Investigation quality
- evidence precision / relevance
- evidence coverage
- unsupported-claim rate
- hypothesis ranking
- root-cause accuracy
- time to useful evidence

## Decision quality
- correct next diagnostic action
- escalation accuracy
- stop/continue decision
- unnecessary-tool rate
- cost / latency

## Automation safety
- false automation rate
- unsafe action proposal rate
- approval-bypass rate
- rollback availability
- blast-radius compliance

## Operational outcome
- MTTD
- MTTR
- error-budget burn
- recurrence rate
- post-action regression

## Replay

Every benchmark scenario should be replayable from a versioned evidence bundle so model, planner and policy changes can be compared against the same incident.
