# Evaluation 2026-11-25 18:38

Scenarios: 6 · runs per scenario: 2 · workers: 4 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 12 |
| Correct requests | 11/12 (92%) |
| Failed requests | 0/12 (0%) |
| Latency p50 | 2.63 s |
| Latency p95 | 4.60 s |
| Latency p99 | 4.60 s |
| Cost / turn | $0.00044 |
| Total cost | $0.00531 |
| Cached input tokens | 85% |
| Correct state (accuracy) | 7/8 (88%) |
| State fields precision | 91% |
| State fields recall | 100% |
| State fields F1 | 95% |
| Correct tool use | 12/12 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 0/12 (0%) |
| Zero results handled | n/a |
| FAQ found (retrieval) | n/a |
| No FAQ answer admitted | 2/2 (100%) |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
|---|---|
| adversarial | 11/12 (92%) |

## What went wrong

- **anthropic:claude-haiku-5-5@low** · `adv-book-sold-out` turn 1 (run 2): travel_types: changed without being asked ([] -> ['360°'])
  - reply: "I can't put you on the 22 December departure because it's sold out, so I can't give you a price for it. The Japan 360° trip (Tokyo, Kyoto, Hiroshima & Osaka by Bullet Train) still has two departures from January: 10–20 January 2027 at €2629 (6 seats left) and 20–30 January 2027 at €2769 (9 seats lef"
