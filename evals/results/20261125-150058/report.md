# Evaluation 2026-11-25 15:17

Scenarios: 78 · runs per scenario: 5 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: embeddings

| Metric | anthropic:claude-haiku-5-5@low |
|---|---|
| Requests (turns) | 430 |
| Correct requests | 423/430 (98%) |
| Failed requests | 0/430 (0%) |
| Latency p50 | 2.07 s |
| Latency p95 | 3.75 s |
| Latency p99 | 4.25 s |
| Cost / turn | $0.00037 |
| Total cost | $0.16124 |
| Cached input tokens | 83% |
| Correct state (accuracy) | 225/230 (98%) |
| State fields precision | 100% |
| State fields recall | 98% |
| State fields F1 | 99% |
| Correct tool use | 430/430 (100%) |
| update_search precision | 100% |
| update_search recall | 100% |
| update_search F1 | 100% |
| Turns with invented facts (lower is better) | 2/430 (0%) |
| Zero results handled | 20/20 (100%) |
| FAQ found (retrieval) | 205/205 (100%) |
| No FAQ answer admitted | 45/45 (100%) |

## Correct requests by category

| Category | anthropic:claude-haiku-5-5@low |
|---|---|
| dates | 15/15 (100%) |
| faq | 15/15 (100%) |
| faq_body_only | 15/15 (100%) |
| faq_destination | 40/40 (100%) |
| faq_italian | 30/30 (100%) |
| faq_multi_turn | 34/35 (97%) |
| faq_near_miss | 20/20 (100%) |
| faq_no_answer | 25/25 (100%) |
| faq_other_language | 15/15 (100%) |
| faq_paraphrase | 70/70 (100%) |
| multi_turn | 30/30 (100%) |
| off_topic | 10/10 (100%) |
| refine | 54/55 (98%) |
| trip_details | 5/5 (100%) |
| vague | 35/35 (100%) |
| zero_results | 10/15 (67%) |

## What went wrong

- **anthropic:claude-haiku-5-5@low** · `hiking-lover` turn 1 (run 2): trip 'Patagonia trek from Torres del Paine to Ushuaia' does not exist
  - reply: "I've filtered the results to Trekking & Hiking trips, and five match. The strongest fit for a hiking-focused trip is the **Patagonia trek from Torres del Paine to Ushuaia** (13 days, from €4169, rated 4.8), which is the most trekking-heavy option. **Madeira 360°: Hiking & Canyoning** (8 days, from €"
- **anthropic:claude-haiku-5-5@low** · `japan-under-900` turn 1 (run 2): max_price: got None, expected {'min': 899, 'max': 900}; expected no results, got 1
  - reply: "There are no Japan trips under €900. The only Japan trip I found is **Japan 360°: Tokyo, Kyoto, Hiroshima & Osaka by Bullet Train** (11 days, rating 4.8), from €2629. I've left the page showing it.\n\nIf the €900 limit matters more than Japan, the closest options are the **Bali 360° trip** (Indonesia,"
- **anthropic:claude-haiku-5-5@low** · `japan-under-900` turn 1 (run 3): max_price: got None, expected {'min': 899, 'max': 900}; expected no results, got 1
  - reply: 'There are no Japan trips under €900. Japan\'s only trip is "Japan 360°: Tokyo, Kyoto, Hiroshima & Osaka by Bullet Train" (11 days, rated 4.8), from €2629.\n\nIf you want to stay under €900, these are the closest matches:\n- **Bali 360°: Seminyak, Ubud, Rice Terraces & a Balinese Cooking Class** (Indones'
- **anthropic:claude-haiku-5-5@low** · `cheap-northern-lights` turn 1 (run 1): max_price: got None, expected {'min': 799, 'max': 800}; expected no results, got 3
  - reply: "No Northern Lights trip is under €800. The cheapest ones start at €1,729 (Iceland, 8 days), €1,759 (Sweden, 7 days) and €2,539 (Canadian Rockies, 6 days). I've removed the budget limit so the page shows those three.\n\nIf you're flexible on the trip type, there are 17 trips under €800, such as Budapes"
- **anthropic:claude-haiku-5-5@low** · `cheap-northern-lights` turn 1 (run 3): max_price: got None, expected {'min': 799, 'max': 800}; expected no results, got 3
  - reply: 'No Northern Lights trip costs under €800. The cheapest Northern Lights trips start at €1,729 (Iceland, 8 days, from €1,729). The page now shows all three Northern Lights trips without the budget limit: Iceland (from €1,729), Sweden: Northern Lights and Lapland (from €1,759), and Canadian Rockies (fr'
- **anthropic:claude-haiku-5-5@low** · `short-snorkelling-trip` turn 1 (run 4): max_days: got None, expected 3; expected no results, got 4
  - reply: "No snorkelling trip is under 3 days. I've removed the length limit, so the list now shows the 4 snorkelling trips, all 13 to 15 days:\n\n- **Madagascar 360°** (14 days, from €1,859, rated 4.9): beaches, jungle, baobabs and lemurs.\n- **Guatemala and Belize** (13 days, from €2,009, rated 5.0): volcanoes"
- **anthropic:claude-haiku-5-5@low** · `faq-in-search-peru` turn 3 (run 5): price €189 not returned by any tool
  - reply: 'No Peru trip is under €2,000. The only Peru trip, Peru 360° (from €2189), is about €189 over budget. Two options:\n\n- **Raise the budget to €2,300:** this brings back the Peru 360° trip.\n- **Keep €2,000 and look elsewhere in America:** this gives 3 trips, though none in Peru.\n\nWhich would you prefer?'
