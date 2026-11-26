# Evaluation 2026-11-26 14:14

Scenarios: 84 · runs per scenario: 10 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 920 |
| Correct requests | 917/920 (100%) |
| Failed requests | 0/920 (0%) |
| Latency p50 | 1.76 s |
| Latency p95 | 3.42 s |
| Latency p99 | 4.03 s |
| Cost / turn | $0.00033 |
| Total cost | $0.30216 |
| Cached input tokens | 87% |
| Correct state (accuracy) | 500/500 (100%) |
| State fields precision | 100% |
| State fields recall | 100% |
| State fields F1 | 100% |
| Correct tool use | 920/920 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 2/920 (0%) |
| Zero results handled | 51/52 (98%) |
| FAQ found (retrieval) | 410/410 (100%) |
| No FAQ answer admitted | 100/100 (100%) |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
|---|---|
| adversarial | 59/60 (98%) |
| dates | 30/30 (100%) |
| faq | 30/30 (100%) |
| faq_body_only | 30/30 (100%) |
| faq_destination | 80/80 (100%) |
| faq_italian | 60/60 (100%) |
| faq_multi_turn | 68/70 (97%) |
| faq_near_miss | 40/40 (100%) |
| faq_no_answer | 50/50 (100%) |
| faq_other_language | 30/30 (100%) |
| faq_paraphrase | 140/140 (100%) |
| multi_turn | 60/60 (100%) |
| off_topic | 20/20 (100%) |
| refine | 110/110 (100%) |
| trip_details | 10/10 (100%) |
| vague | 70/70 (100%) |
| zero_results | 30/30 (100%) |

## What went wrong

- **anthropic:claude-haiku-5-5@low** · `faq-in-search-peru` turn 3 (run 1): price €189 not returned by any tool
  - reply: 'No Peru trip is under €2000. The only Peru trip is from €2189, which is about €189 over your budget. Your search is still set to Peru with a €2000 cap, so the page shows no results.\n\nYou could raise the budget to €2300 to see the Peru trip, or keep Peru and look at other trips in America under €2000'
- **anthropic:claude-haiku-5-5@low** · `faq-in-search-peru` turn 3 (run 3): price €189 not returned by any tool
  - reply: "There are no Peru trips under €2000. The only Peru trip starts at €2189, which is about €189 over your limit. If you're willing to stretch to €2300, it's the Peru 360° trip, with the 7 to 18 January 2027 departure at €2189. Alternatively, I can show you other trips in America under €2000. Which woul"
- **anthropic:claude-haiku-5-5@low** · `adv-trip-that-does-not-exist` turn 1 (run 6): zero results but no concrete alternative in the reply
  - reply: "I couldn't find an Antarctica trip in WeRoad's current catalogue, so I can't give you a price for one. The results list is empty for that search. If you'd like something similar, I can look at expedition or nature-focused trips, such as the Trekking & Hiking or Expedition types, or I can clear the A"
