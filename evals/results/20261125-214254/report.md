# Evaluation 2026-11-25 21:43

Scenarios: 6 · runs per scenario: 5 · workers: 4 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 30 |
| Correct requests | 30/30 (100%) |
| Failed requests | 0/30 (0%) |
| Latency p50 | 2.71 s |
| Latency p95 | 4.20 s |
| Latency p99 | 5.11 s |
| Cost / turn | $0.00055 |
| Total cost | $0.01638 |
| Cached input tokens | 74% |
| Correct state (accuracy) | 20/20 (100%) |
| State fields precision | 100% |
| State fields recall | 100% |
| State fields F1 | 100% |
| Correct tool use | 30/30 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 0/30 (0%) |
| Zero results handled | 1/1 (100%) |
| FAQ found (retrieval) | n/a |
| No FAQ answer admitted | 5/5 (100%) |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
|---|---|
| adversarial | 30/30 (100%) |

## What went wrong

Nothing: every turn passed every check.
