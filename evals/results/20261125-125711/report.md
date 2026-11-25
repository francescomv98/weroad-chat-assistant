# Evaluation 2026-11-25 13:04

Scenarios: 78 · runs per scenario: 2 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | gpt-4.1-mini |
|---|---|
| Requests (turns) | 172 |
| Correct requests | 171/172 (99%) |
| Failed requests | 0/172 (0%) |
| Latency p50 | 2.46 s |
| Latency p95 | 3.32 s |
| Latency p99 | 4.05 s |
| Cost / turn | $0.00124 |
| Total cost | $0.21323 |
| Cached input tokens | 50% |
| Correct state (accuracy) | 92/92 (100%) |
| State fields precision | 100% |
| State fields recall | 100% |
| State fields F1 | 100% |
| Correct tool use | 172/172 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 0/172 (0%) |
| Zero results handled | 11/12 (92%) |
| FAQ found (retrieval) | 82/82 (100%) |
| No FAQ answer admitted | 18/18 (100%) |

## Correct requests by category

| Category | gpt-4.1-mini |
|---|---|
| dates | 6/6 (100%) |
| faq | 6/6 (100%) |
| faq_body_only | 6/6 (100%) |
| faq_destination | 16/16 (100%) |
| faq_italian | 12/12 (100%) |
| faq_multi_turn | 14/14 (100%) |
| faq_near_miss | 8/8 (100%) |
| faq_no_answer | 10/10 (100%) |
| faq_other_language | 6/6 (100%) |
| faq_paraphrase | 28/28 (100%) |
| multi_turn | 12/12 (100%) |
| off_topic | 4/4 (100%) |
| refine | 22/22 (100%) |
| trip_details | 2/2 (100%) |
| vague | 14/14 (100%) |
| zero_results | 5/6 (83%) |

## What went wrong

- **gpt-4.1-mini** · `cheap-northern-lights` turn 1 (run 1): zero results but no concrete alternative in the reply
  - reply: 'There are no Northern Lights trips under €800 currently available. The closest option is to relax the travel type restriction. Would you like me to show you trips under €800 regardless of type? Or would you prefer Northern Lights trips with no budget limit?'
