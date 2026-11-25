# Evaluation 2026-11-25 14:55

Scenarios: 78 · runs per scenario: 2 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | gpt-4.1-mini | anthropic:claude-haiku-5-5 |
|---|---|---|
| Requests (turns) | 172 | 172 |
| Correct requests | 170/172 (99%) | 172/172 (100%) |
| Failed requests | 0/172 (0%) | 0/172 (0%) |
| Latency p50 | 2.05 s | 2.16 s |
| Latency p95 | 2.74 s | 3.89 s |
| Latency p99 | 3.75 s | 5.59 s |
| Cost / turn | $0.00120 | $0.00053 |
| Total cost | $0.20699 | $0.09051 |
| Cached input tokens | 53% | 69% |
| Correct state (accuracy) | 90/92 (98%) | 92/92 (100%) |
| State fields precision | 95% | 100% |
| State fields recall | 99% | 100% |
| State fields F1 | 97% | 100% |
| Correct tool use | 172/172 (100%) | 172/172 (100%) |
| update_search precision | 100% | 100% |
| update_search recall | 100% | 100% |
| update_search F1 | 100% | 100% |
| Turns with invented facts (lower is better) | 0/172 (0%) | 0/172 (0%) |
| Zero results handled | 11/11 (100%) | 10/10 (100%) |
| FAQ found (retrieval) | 82/82 (100%) | 82/82 (100%) |
| No FAQ answer admitted | 18/18 (100%) | 18/18 (100%) |

## Correct requests by category

| Category | gpt-4.1-mini | anthropic:claude-haiku-5-5 |
|---|---|---|
| dates | 6/6 (100%) | 6/6 (100%) |
| faq | 6/6 (100%) | 6/6 (100%) |
| faq_body_only | 6/6 (100%) | 6/6 (100%) |
| faq_destination | 16/16 (100%) | 16/16 (100%) |
| faq_italian | 12/12 (100%) | 12/12 (100%) |
| faq_multi_turn | 14/14 (100%) | 14/14 (100%) |
| faq_near_miss | 8/8 (100%) | 8/8 (100%) |
| faq_no_answer | 10/10 (100%) | 10/10 (100%) |
| faq_other_language | 6/6 (100%) | 6/6 (100%) |
| faq_paraphrase | 28/28 (100%) | 28/28 (100%) |
| multi_turn | 12/12 (100%) | 12/12 (100%) |
| off_topic | 4/4 (100%) | 4/4 (100%) |
| refine | 22/22 (100%) | 22/22 (100%) |
| trip_details | 2/2 (100%) | 2/2 (100%) |
| vague | 12/14 (86%) | 14/14 (100%) |
| zero_results | 6/6 (100%) | 6/6 (100%) |

## What went wrong

- **gpt-4.1-mini** · `vague-adventure-then-easy` turn 1 (run 1): travel_types: got [], expected {'contains': 'Active'}
  - reply: 'For an adventurous trip, here are some great options: Egypt 360° offers pyramids, a night train, and the Red Sea in 9 days from €1049; Vietnam 360° covers from Hanoi to Ho Chi Minh City, 13 days from €1549; Kyrgyzstan 360° explores yurt nights and eagle hunters in 9 days from €1189. Would you like m'
- **gpt-4.1-mini** · `vague-adventure-then-easy` turn 2 (run 1): moods.culture: changed without being asked (0 -> None); moods.history: changed without being asked (0 -> None); moods.nature: changed without being asked (0 -> None); moods.party: changed without being asked (0 -> None); moods.relax: changed without being asked (0 -> None)
  - reply: 'I found 13 adventurous trips with low physical demand. Highlights include Copenhagen Weekend with fairytale charm and Tivoli Gardens from €359, Budapest Weekend "The Pearl of the East" from €329, and Cape Verde Beach Life on Sal Island for 8 days from €1089. Would you like details on any of these or'
