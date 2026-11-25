# Evaluation 2026-11-25 16:16

Scenarios: 11 · runs per scenario: 1 · workers: 4 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 11 |
| Correct requests | 10/11 (91%) |
| Failed requests | 0/11 (0%) |
| Latency p50 | 1.85 s |
| Latency p95 | 3.14 s |
| Latency p99 | 3.14 s |
| Cost / turn | $0.00071 |
| Total cost | $0.00776 |
| Cached input tokens | 44% |
| Correct state (accuracy) | 11/11 (100%) |
| State fields precision | 100% |
| State fields recall | 100% |
| State fields F1 | 100% |
| Correct tool use | 11/11 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 1/11 (9%) |
| Zero results handled | n/a |
| FAQ found (retrieval) | n/a |
| No FAQ answer admitted | n/a |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
|---|---|
| refine | 10/11 (91%) |

## What went wrong

- **anthropic:claude-haiku-5-5@low** · `italian-beach-in-asia` turn 1 (run 1): trip 'Maldive – Beach Life a Vaavu Atoll' does not exist
  - reply: 'Ho trovato 2 viaggi al mare in Asia, filtrati per "Beach Life":\n\n- **Maldive – Beach Life a Vaavu Atoll** (7 giorni, rating 4.8): da €1409, con delfini, tartarughe e tramonti sulle sandbank. Partenze da €1409 a gennaio 2027.\n- **Filippine – 360°: Bohol, Palawan e una notte sotto le stelle** (12 gior'
