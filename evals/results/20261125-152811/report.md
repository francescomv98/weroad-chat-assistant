# Evaluation 2026-11-25 15:34

Scenarios: 78 · runs per scenario: 2 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 172 |
| Correct requests | 172/172 (100%) |
| Failed requests | 0/172 (0%) |
| Latency p50 | 2.00 s |
| Latency p95 | 3.66 s |
| Latency p99 | 4.39 s |
| Cost / turn | $0.00046 |
| Total cost | $0.07927 |
| Cached input tokens | 72% |
| Correct state (accuracy) | 92/92 (100%) |
| State fields precision | 100% |
| State fields recall | 100% |
| State fields F1 | 100% |
| Correct tool use | 172/172 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 0/172 (0%) |
| Zero results handled | 10/10 (100%) |
| FAQ found (retrieval) | 82/82 (100%) |
| No FAQ answer admitted | 18/18 (100%) |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
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
| zero_results | 6/6 (100%) |

## What went wrong

Nothing: every turn passed every check.
