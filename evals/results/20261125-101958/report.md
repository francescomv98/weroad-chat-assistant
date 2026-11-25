# Evaluation 2026-11-25 10:24

Scenarios: 49 · runs per scenario: 5 · workers: 4 · frozen today: 2026-11-24 · FAQ retrievers: index, embeddings

| Metric | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| Requests (turns) | 265 | 265 |
| Correct requests | 253/265 (95%) | 256/265 (97%) |
| Failed requests | 0/265 (0%) | 0/265 (0%) |
| Latency p50 | 1.79 s | 2.09 s |
| Latency p95 | 2.43 s | 2.67 s |
| Latency p99 | 2.73 s | 3.15 s |
| Cost / turn | $0.00082 | $0.00118 |
| Total cost | $0.21649 | $0.31345 |
| Correct state (accuracy) | 65/65 (100%) | 65/65 (100%) |
| State fields precision | 100% | 100% |
| State fields recall | 100% | 100% |
| State fields F1 | 100% | 100% |
| Correct tool use | 265/265 (100%) | 263/265 (99%) |
| update_search precision | 100% | 100% |
| update_search recall | 100% | 100% |
| update_search F1 | 100% | 100% |
| Turns with invented facts (lower is better) | 1/265 (0%) | 0/265 (0%) |
| Zero results handled | 5/5 (100%) | 5/5 (100%) |
| FAQ found (retrieval) | 202/205 (99%) | 200/205 (98%) |
| No FAQ answer admitted | 37/45 (82%) | 41/45 (91%) |

## Correct requests by category

| Category | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| faq | 15/15 (100%) | 15/15 (100%) |
| faq_body_only | 12/15 (80%) | 15/15 (100%) |
| faq_destination | 40/40 (100%) | 40/40 (100%) |
| faq_italian | 30/30 (100%) | 30/30 (100%) |
| faq_multi_turn | 34/35 (97%) | 33/35 (94%) |
| faq_near_miss | 13/20 (65%) | 18/20 (90%) |
| faq_no_answer | 24/25 (96%) | 23/25 (92%) |
| faq_other_language | 15/15 (100%) | 15/15 (100%) |
| faq_paraphrase | 70/70 (100%) | 67/70 (96%) |

## What went wrong

- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 1): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: 'On WeRoad trips, you usually stay in locally owned accommodations such as hotels, apartments, guesthouses, and hostels. This helps you experience local culture and support the local economy. The specific accommodation details, including bathroom arrangements, will be shared with you by your Group Le'
- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 2): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: 'On WeRoad trips, accommodation is usually locally owned, such as hotels, apartments, guesthouses, and hostels, providing a genuine local experience and supporting the local economy. The same standard is maintained across trips in the same destination. Your Group Leader will share the detailed list o'
- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 5): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: 'On WeRoad trips, accommodation typically includes locally owned hotels, apartments, guesthouses, and hostels, aiming to provide a local cultural experience and support the local economy. The Group Leader will share the accommodation details, including bathroom arrangements, 2-5 days before departure'
- **gpt-4.1-mini · index** · `faq-near-japan-weather` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: 'In Japan, they use Type A and Type B plugs. Type A has two flat parallel pins, while Type B has the same two pins plus a grounding pin. The voltage is 100V with a frequency of 50-60Hz. You might need an adapter and possibly a voltage converter for your devices. Check your electronics for compatibili'
- **gpt-4.1-mini · index** · `faq-near-japan-weather` turn 1 (run 3): no FAQ answers this, but the reply doesn't say so
  - reply: 'Regarding Japan, the plugs used are Type A and Type B. Type A has two flat parallel pins, and Type B adds a grounding pin. The voltage is 100V with a frequency of 50-60Hz, so you might need an adapter or voltage converter for some devices. If you also want info about the weather in Japan, I can chec'
- **gpt-4.1-mini · index** · `faq-near-japan-weather` turn 1 (run 4): no FAQ answers this, but the reply doesn't say so
  - reply: 'I found information about the type of plugs used in Japan, but not on the weather. Would you like me to help you find trips to Japan instead?'
- **gpt-4.1-mini · index** · `faq-near-japan-weather` turn 1 (run 5): no FAQ answers this, but the reply doesn't say so
  - reply: 'I found information about electrical plugs in Japan, but not the weather. For weather details in Japan, I suggest checking a dedicated weather website or app. If you want, I can help you find a trip to Japan instead. Would you like that?'
- **gpt-4.1-mini · index** · `faq-near-morocco-plugs` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: "I found information about tipping in Morocco, but not about the plugs used there. For plug and socket details in Morocco, I recommend checking WeRoad's help center or travel resources specifically about electrical standards. Can I assist you with finding trips to Morocco or another question?"
- **gpt-4.1-mini · index** · `faq-near-morocco-plugs` turn 1 (run 3): no FAQ answers this, but the reply doesn't say so
  - reply: "In Morocco, the specific plug types are not detailed in the available FAQs. However, for a similar region like Greece, the plugs used are Types C and F, which have two round pins, with a standard voltage of 230 V and frequency of 50 Hz. It's a good idea to bring a universal adapter to ensure your de"
- **gpt-4.1-mini · index** · `faq-near-morocco-plugs` turn 1 (run 5): no FAQ answers this, but the reply doesn't say so
  - reply: 'In Morocco, the answer about plugs is not in the FAQ I accessed. For WeRoad trips to Morocco, I recommend checking local sources or bringing a universal adapter to be safe. If you want, I can help you find trips to Morocco or nearby destinations!'
- **gpt-4.1-mini · index** · `faq-none-dog` turn 1 (run 2): no FAQ answers this, but the reply doesn't say so
  - reply: "WeRoad trips generally don't allow dogs, as the trips involve group travel and accommodations that may not accommodate pets. For specific details or exceptions, I recommend checking WeRoad's official policies or contacting their support directly. Can I help you find a trip based on your travel prefe"
- **gpt-4.1-mini · index** · `faq-in-search-peru` turn 3 (run 1): price €2300 not returned by any tool
  - reply: 'Currently, there are no trips to Peru under €2000. The closest option is the Peru 360° trip, priced at €2189. You could either increase your budget slightly to around €2300 to include this trip or consider other destinations in America within your budget. Which would you prefer?'
- **gpt-4.1-mini · embeddings** · `faq-plane-tickets` turn 1 (run 2): expected FAQ 'Are flights included?', got ["Can I find out my travel groups' flights?", 'Will I be sharing a room?', 'Can I cancel my booking?']
  - reply: "You don't need to book your own plane tickets for WeRoad trips. You can coordinate with your travel group by sharing and viewing flight details in your personal area or in the trip message space on the website. Your Travel Coordinator is also available to help with flight questions. Let me know if y"
- **gpt-4.1-mini · embeddings** · `faq-plane-tickets` turn 1 (run 3): expected FAQ 'Are flights included?', got ['Can I cancel my booking?', 'Can I modify my booking?', "Can I find out my travel groups' flights?"]
  - reply: "You do need to book your own plane tickets for WeRoad trips. However, once you book, you can add your flight details in your personal area, and see others' flight plans anonymously to coordinate. If you want more details, I can share the link to this info."
- **gpt-4.1-mini · embeddings** · `faq-plane-tickets` turn 1 (run 5): expected FAQ 'Are flights included?', got ["Can I find out my travel groups' flights?", 'Will I be sharing a room?', 'Can I see who’s in the group before I book the trip?']
  - reply: "You do need to book your own plane tickets for a WeRoad trip. Once booked, you can share your flight details with the group through your personal area on WeRoad's website, making it easier for everyone to coordinate. If you'd like more details, I can share the link to WeRoad's FAQ on this topic. Wou"
- **gpt-4.1-mini · embeddings** · `faq-near-morocco-plugs` turn 1 (run 3): no FAQ answers this, but the reply doesn't say so
  - reply: "The FAQs I found did not have the exact answer for Morocco's plug types. Typically, Morocco uses Type C and Type E plugs with a standard voltage of 220V and frequency of 50Hz. I suggest bringing a universal adapter to ensure your devices can be charged and used without issues. For more detailed info"
- **gpt-4.1-mini · embeddings** · `faq-near-morocco-plugs` turn 1 (run 4): no FAQ answers this, but the reply doesn't say so
  - reply: "The FAQs did not have specific information on plugs used in Morocco. Generally, it is recommended to bring a universal adapter when traveling, as plug types can vary. For detailed and specific info, you may want to check WeRoad's help center or your travel guide. Can I help you find a trip to Morocc"
- **gpt-4.1-mini · embeddings** · `faq-none-insurance` turn 1 (run 4): no FAQ answers this, but the reply doesn't say so
  - reply: "WeRoad's FAQs don't specifically mention travel insurance requirements for trips. I recommend checking with your personal insurance provider or WeRoad's customer support for tailored advice on travel insurance for your trip. If you want, I can help with other trip-related info!"
- **gpt-4.1-mini · embeddings** · `faq-none-dog` turn 1 (run 4): no FAQ answers this, but the reply doesn't say so
  - reply: "The FAQs do not specify if dogs are allowed on WeRoad trips. For this specific information, I recommend contacting WeRoad's customer support directly for the policy on bringing pets. Meanwhile, I can help you find trips or answer other questions about WeRoad trips."
- **gpt-4.1-mini · embeddings** · `faq-two-questions` turn 2 (run 1): did not call get_faqs; expected FAQ 'Can I cancel my booking?', got no FAQ
  - reply: "Yes, you can cancel your booking from your MyWeRoad area. If the tour is confirmed, the amounts paid are non-refundable, but you can move your booking to another trip free of charge up to 31 days before departure. If the tour is not confirmed yet, you can cancel and get a full refund of what you've "
- **gpt-4.1-mini · embeddings** · `faq-two-questions` turn 2 (run 4): did not call get_faqs; expected FAQ 'Can I cancel my booking?', got no FAQ
  - reply: 'You can cancel your booking through your MyWeRoad Personal Area. If the tour is confirmed, amounts paid are non-refundable, but you can move your booking to another trip free of charge up to 31 days before departure. If the tour is not confirmed, you get a full refund (excluding any Flexible Cancell'
