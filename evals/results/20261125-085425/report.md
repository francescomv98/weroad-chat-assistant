# Evaluation 2026-11-25 09:00

Scenarios: 42 · runs per scenario: 2 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: index, embeddings

| Metric | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| Requests (turns) | 90 | 90 |
| Correct requests | 88/90 (98%) | 88/90 (98%) |
| Failed requests | 0/90 (0%) | 0/90 (0%) |
| Latency p50 | 1.97 s | 2.22 s |
| Latency p95 | 2.65 s | 3.34 s |
| Latency p99 | 2.84 s | 3.46 s |
| Cost / turn | $0.00090 | $0.00118 |
| Total cost | $0.08064 | $0.10662 |
| Correct state (accuracy) | 63/64 (98%) | 62/64 (97%) |
| State fields precision | 100% | 99% |
| State fields recall | 99% | 99% |
| State fields F1 | 99% | 99% |
| Correct tool use | 90/90 (100%) | 90/90 (100%) |
| update_search precision | 100% | 100% |
| update_search recall | 100% | 100% |
| update_search F1 | 100% | 100% |
| Turns with invented facts (lower is better) | 0/90 (0%) | 0/90 (0%) |
| Zero results handled | 9/9 (100%) | 9/9 (100%) |
| FAQ found (retrieval) | 34/34 (100%) | 34/34 (100%) |
| No FAQ answer admitted | 3/4 (75%) | 4/4 (100%) |

## Correct requests by category

| Category | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| dates | 6/6 (100%) | 6/6 (100%) |
| faq | 6/6 (100%) | 6/6 (100%) |
| faq_destination | 6/6 (100%) | 6/6 (100%) |
| faq_italian | 6/6 (100%) | 6/6 (100%) |
| faq_no_answer | 3/4 (75%) | 4/4 (100%) |
| faq_paraphrase | 16/16 (100%) | 16/16 (100%) |
| multi_turn | 12/12 (100%) | 12/12 (100%) |
| off_topic | 4/4 (100%) | 4/4 (100%) |
| refine | 21/22 (95%) | 21/22 (95%) |
| trip_details | 2/2 (100%) | 2/2 (100%) |
| zero_results | 6/6 (100%) | 5/6 (83%) |

## What went wrong

- **gpt-4.1-mini · index** · `hiking-lover` turn 1 (run 2): travel_types: got [], expected {'contains': 'Trekking'}
  - reply: 'I found 9 trekking trips for you. Highlights include Vietnam 360° with extensive trekking from Hanoi to Ho Chi Minh City, Kyrgyzstan 360° featuring yurt nights and eagle hunters, and Patagonia hiking Torres del Paine to Ushuaia at the End of the World for an epic adventure. Would you prefer shorter '
- **gpt-4.1-mini · index** · `faq-none-tap-water` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: "The FAQs I have include information about internet and SIM cards in Mexico but do not specify if tap water is safe to drink. For safety, it's best to check local advice when you arrive or consider bottled water. If you want, I can help you find trips to Mexico."
- **gpt-4.1-mini · embeddings** · `hiking-lover` turn 1 (run 1): travel_types: got [], expected {'contains': 'Trekking'}
  - reply: "I found 5 trips with a strong focus on trekking and hiking for you. The Patagonia trip in Argentina offers extensive trekking over 13 days, great if you want a long adventure. There's a 9-day Nepal trip featuring the Annapurna sunrise, perfect for immersive hikes in the Himalayas. For something shor"
- **gpt-4.1-mini · embeddings** · `cheap-northern-lights` turn 1 (run 1): moods.nature: changed without being asked (None -> 60)
  - reply: 'There are no Northern Lights trips under €800, but I found 4 options under €800 if we relax the travel type: a cozy Copenhagen weekend for €359, a Transylvania road trip for €539, an Andalusia weekend for €389, and a Balkan Christmas Markets trip for €739. Would you like to see any of those or shoul'
