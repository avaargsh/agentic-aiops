# Incident Scenario Corpus

This directory is reserved for replayable AIOps evaluation scenarios.

A scenario should separate:

1. frozen incident/evidence inputs,
2. expected bounded decision behavior,
3. automation eligibility,
4. expected required tools,
5. recovery expectation,
6. recorded system outcome.

The first metrics implemented are:

- Unsupported Supported-Claim Rate
- False Automation Rate
- Escalation Accuracy
- Unnecessary Tool Rate
- Recovery Success Rate

Synthetic fixtures are useful for contract tests but must not be presented as production-quality benchmark results.
