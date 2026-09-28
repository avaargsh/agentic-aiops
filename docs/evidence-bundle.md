# Replayable Evidence Bundle

An incident investigation should be reproducible without re-querying the live production system.

The Evidence Bundle is the portable replay unit.

```text
Incident
  |
  +-- Evidence
  +-- Hypotheses
  +-- Topology Entities
  +-- Topology Edges
  +-- Change Events
  +-- Metadata
```

## Why

Without a versioned evidence bundle, a model or planner change is hard to evaluate fairly because the live system changes between runs.

A replayable bundle supports:

- regression tests,
- model/provider comparison,
- unsupported-claim analysis,
- Decision Plane experiments,
- postmortem review,
- audit.

## Evidence vs hypothesis

Evidence stores observations.

Hypotheses store interpretations and explicitly reference evidence IDs.

A fluent hypothesis with no supporting evidence remains unverified.

## Topology

Entities and edges make incident scope machine-readable:

```text
Service -> Database
Pod -> Node
Workload -> GPU
GPU -> NIC
NIC -> Leaf
```

## Change context

Change events capture deployments, configuration updates, scaling actions or infrastructure changes that may correlate with an incident.

## Replay

`investigation_from_bundle()` reconstructs an Investigation from a frozen bundle. Future benchmark runners can execute different planners/reasoners against the same bundle.
