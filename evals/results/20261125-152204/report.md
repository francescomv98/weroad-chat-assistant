# Evaluation 2026-11-25 15:26

Scenarios: 17 · runs per scenario: 5 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 100 |
| Correct requests | 99/100 (99%) |
| Failed requests | 0/100 (0%) |
| Latency p50 | 1.95 s |
| Latency p95 | 3.03 s |
| Latency p99 | 3.65 s |
| Cost / turn | $0.00033 |
| Total cost | $0.03342 |
| Cached input tokens | 88% |
| Correct state (accuracy) | 100/100 (100%) |
| State fields precision | 100% |
| State fields recall | 100% |
| State fields F1 | 100% |
| Correct tool use | 100/100 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 1/100 (1%) |
| Zero results handled | 15/15 (100%) |
| FAQ found (retrieval) | n/a |
| No FAQ answer admitted | n/a |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
|---|---|
| multi_turn | 30/30 (100%) |
| refine | 54/55 (98%) |
| zero_results | 15/15 (100%) |

## What went wrong

- **anthropic:claude-haiku-5-5@low** · `italian-beach-in-asia` turn 1 (run 1): trip 'Maldive, Vaavu Atoll' does not exist
  - reply: 'Ho trovato 2 viaggi Beach Life in Asia:\n\n- **Maldive, Vaavu Atoll** (7 giorni, valutazione 4.8): delfini, tartarughe e banchi di sabbia al tramonto. Partenza da €1409, con date come 06/01/2027 a €1409.\n- **Filippine, 360°** (12 giorni, valutazione 4.7): tarsier a Bohol, Palawan e una notte sotto le '
