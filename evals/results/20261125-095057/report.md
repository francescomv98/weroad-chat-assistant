# Evaluation 2026-11-25 09:58

Scenarios: 49 · runs per scenario: 2 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: index, embeddings

| Metric | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| Requests (turns) | 106 | 106 |
| Correct requests | 100/106 (94%) | 102/106 (96%) |
| Failed requests | 0/106 (0%) | 0/106 (0%) |
| Latency p50 | 1.93 s | 2.26 s |
| Latency p95 | 2.59 s | 2.87 s |
| Latency p99 | 2.94 s | 3.34 s |
| Cost / turn | $0.00086 | $0.00118 |
| Total cost | $0.09166 | $0.12476 |
| Correct state (accuracy) | 26/26 (100%) | 26/26 (100%) |
| State fields precision | 100% | 100% |
| State fields recall | 100% | 100% |
| State fields F1 | 100% | 100% |
| Correct tool use | 106/106 (100%) | 105/106 (99%) |
| update_search precision | 100% | 100% |
| update_search recall | 100% | 100% |
| update_search F1 | 100% | 100% |
| Turns with invented facts (lower is better) | 0/106 (0%) | 0/106 (0%) |
| Zero results handled | 2/2 (100%) | 2/2 (100%) |
| FAQ found (retrieval) | 80/82 (98%) | 80/82 (98%) |
| No FAQ answer admitted | 14/18 (78%) | 16/18 (89%) |

## Correct requests by category

| Category | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| faq | 6/6 (100%) | 6/6 (100%) |
| faq_body_only | 4/6 (67%) | 6/6 (100%) |
| faq_destination | 16/16 (100%) | 16/16 (100%) |
| faq_italian | 12/12 (100%) | 12/12 (100%) |
| faq_multi_turn | 14/14 (100%) | 13/14 (93%) |
| faq_near_miss | 5/8 (62%) | 8/8 (100%) |
| faq_no_answer | 9/10 (90%) | 8/10 (80%) |
| faq_other_language | 6/6 (100%) | 6/6 (100%) |
| faq_paraphrase | 28/28 (100%) | 27/28 (96%) |

## What went wrong

- **gpt-4.1-mini · index** · `faq-none-visa-india` turn 1 (run 2): no FAQ answers this, but the reply doesn't say so
  - reply: "I can only provide information from WeRoad's FAQs about flights, bookings, payments, group info, accommodation, and destination tips like currency, weather, plugs, tipping, and internet. For visa requirements to India, I recommend checking official government sources or WeRoad's help centre. Can I h"
- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 1): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: "On WeRoad trips, you'll usually stay in locally owned accommodation like hotels, apartments, guesthouses, and hostels. The accommodation standards are consistent across trips in the same destination. Your Group Leader will share the accommodation details, including whether you have a private bathroo"
- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 2): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: 'On WeRoad trips, you usually stay in locally owned accommodations like hotels, apartments, guesthouses, and hostels, which support the local culture and economy. The accommodation standards are consistent within the same destination. Your Group Leader will share the list of accommodations with you 2'
- **gpt-4.1-mini · index** · `faq-near-japan-weather` turn 1 (run 2): no FAQ answers this, but the reply doesn't say so
  - reply: 'I found information about the plugs used in Japan but not specific weather details. For plugs, Japan uses Type A and Type B plugs with 100V voltage. If you want, I can help you find trips to Japan or answer other travel-related questions!'
- **gpt-4.1-mini · index** · `faq-near-morocco-plugs` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: "I found information about tipping in Morocco, but nothing specific about plugs. For plug types in Morocco, I recommend checking WeRoad's help center or asking their support directly. Can I help you find a trip to Morocco or elsewhere?"
- **gpt-4.1-mini · index** · `faq-near-morocco-plugs` turn 1 (run 2): no FAQ answers this, but the reply doesn't say so
  - reply: "In Morocco, you typically need Type C and Type E plugs with two or three round pins, and the standard voltage is 220V. It's recommended to bring a universal adapter if your devices use different plug types. If you want, I can also help find trips to Morocco for you."
- **gpt-4.1-mini · embeddings** · `faq-plane-tickets` turn 1 (run 2): expected FAQ 'Are flights included?', got ["Can I find out my travel groups' flights?", 'Will I be sharing a room?', 'Can I cancel my booking?']
  - reply: "You need to book your own plane tickets for WeRoad trips. Once you've booked, you can add your flight details in your personal area and see other group members' flight info to coordinate. You can also discuss flights with your travel mates and Travel Coordinator in the trip messages on the WeRoad we"
- **gpt-4.1-mini · embeddings** · `faq-none-insurance` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: "WeRoad's FAQs do not explicitly state that travel insurance is required for the trip. For specific details on insurance, I recommend checking your booking details or contacting WeRoad support directly to confirm if it's mandatory for your trip. If you have other questions about booking or trips, fee"
- **gpt-4.1-mini · embeddings** · `faq-none-insurance` turn 1 (run 2): no FAQ answers this, but the reply doesn't say so
  - reply: "WeRoad's FAQs do not explicitly mention travel insurance requirements. For detailed and specific information about whether you need travel insurance for your trip, I recommend checking WeRoad's official help centre or contacting them directly at hello@weroad.com. Can I help you find a trip to explor"
- **gpt-4.1-mini · embeddings** · `faq-two-questions` turn 2 (run 2): did not call get_faqs; expected FAQ 'Can I cancel my booking?', got no FAQ
  - reply: 'I found that you can cancel your booking through your MyWeRoad Personal Area. If the tour is confirmed, amounts paid are generally non-refundable, but you can move your booking to another trip free of charge up to 31 days before departure. If the tour is not confirmed yet, refunds are available. The'
