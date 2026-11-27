# Evaluation 2026-11-27 12:35

Scenarios: 86 · runs per scenario: 10 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 940 |
| Correct requests | 940/940 (100%) |
| Failed requests | 0/940 (0%) |
| Latency p50 | 2.18 s |
| Latency p95 | 3.64 s |
| Latency p99 | 4.52 s |
| Cost / turn | $0.00032 |
| Total cost | $0.29681 |
| Cached input tokens | 89% |
| Correct state (accuracy) | 500/500 (100%) |
| State fields precision | 100% |
| State fields recall | 100% |
| State fields F1 | 100% |
| Correct tool use | 940/940 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 0/940 (0%) |
| Zero results handled | 50/50 (100%) |
| FAQ found (retrieval) | 410/410 (100%) |
| No FAQ answer admitted | 120/120 (100%) |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
|---|---|
| adversarial | 60/60 (100%) |
| dates | 30/30 (100%) |
| faq | 30/30 (100%) |
| faq_body_only | 30/30 (100%) |
| faq_destination | 80/80 (100%) |
| faq_italian | 60/60 (100%) |
| faq_multi_turn | 70/70 (100%) |
| faq_near_miss | 40/40 (100%) |
| faq_no_answer | 70/70 (100%) |
| faq_other_language | 30/30 (100%) |
| faq_paraphrase | 140/140 (100%) |
| multi_turn | 60/60 (100%) |
| off_topic | 20/20 (100%) |
| refine | 110/110 (100%) |
| trip_details | 10/10 (100%) |
| vague | 70/70 (100%) |
| zero_results | 30/30 (100%) |

## What went wrong

Nothing: every turn passed every check.
