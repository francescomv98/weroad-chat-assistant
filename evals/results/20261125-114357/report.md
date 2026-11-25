# Evaluation 2026-11-25 12:17

Scenarios: 78 · runs per scenario: 5 · workers: 1 · frozen today: 2026-11-24 · FAQ retrievers: index, embeddings

| Metric | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| Requests (turns) | 430 | 430 |
| Correct requests | 419/430 (97%) | 422/430 (98%) |
| Failed requests | 0/430 (0%) | 0/430 (0%) |
| Latency p50 | 1.95 s | 2.33 s |
| Latency p95 | 2.75 s | 3.44 s |
| Latency p99 | 3.62 s | 4.58 s |
| Cost / turn | $0.00092 | $0.00108 |
| Total cost | $0.39471 | $0.46566 |
| Correct state (accuracy) | 230/230 (100%) | 229/230 (100%) |
| State fields precision | 100% | 100% |
| State fields recall | 100% | 100% |
| State fields F1 | 100% | 100% |
| Correct tool use | 430/430 (100%) | 428/430 (100%) |
| update_search precision | 100% | 100% |
| update_search recall | 100% | 100% |
| update_search F1 | 100% | 100% |
| Turns with invented facts (lower is better) | 0/430 (0%) | 2/430 (0%) |
| Zero results handled | 29/29 (100%) | 29/29 (100%) |
| FAQ found (retrieval) | 197/205 (96%) | 200/205 (98%) |
| No FAQ answer admitted | 42/45 (93%) | 45/45 (100%) |

## Correct requests by category

| Category | gpt-4.1-mini · index | gpt-4.1-mini · embeddings |
|---|---|---|
| dates | 15/15 (100%) | 15/15 (100%) |
| faq | 15/15 (100%) | 15/15 (100%) |
| faq_body_only | 12/15 (80%) | 15/15 (100%) |
| faq_destination | 35/40 (88%) | 40/40 (100%) |
| faq_italian | 30/30 (100%) | 29/30 (97%) |
| faq_multi_turn | 35/35 (100%) | 33/35 (94%) |
| faq_near_miss | 17/20 (85%) | 20/20 (100%) |
| faq_no_answer | 25/25 (100%) | 25/25 (100%) |
| faq_other_language | 15/15 (100%) | 15/15 (100%) |
| faq_paraphrase | 70/70 (100%) | 67/70 (96%) |
| multi_turn | 30/30 (100%) | 30/30 (100%) |
| off_topic | 10/10 (100%) | 10/10 (100%) |
| refine | 55/55 (100%) | 54/55 (98%) |
| trip_details | 5/5 (100%) | 5/5 (100%) |
| vague | 35/35 (100%) | 34/35 (97%) |
| zero_results | 15/15 (100%) | 15/15 (100%) |

## What went wrong

- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 1): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: 'On WeRoad trips, accommodation is usually locally owned hotels, apartments, guesthouses, or hostels, chosen to maintain a consistent standard and to support the local economy. Whether you have a private bathroom can depend on the specific accommodation for your trip, which will be shared with you by'
- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 2): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: 'On WeRoad trips, accommodation is usually locally owned like hotels, apartments, guesthouses, and hostels to immerse you in local culture and support the local economy. The details about your accommodation, including whether you have a private bathroom, will be shared by your Group Leader 2-5 days b'
- **gpt-4.1-mini · index** · `faq-body-bathroom` turn 1 (run 3): expected FAQ 'Will I be sharing a room?', got ['What type of accommodation should I expect on your trips?']
  - reply: 'On WeRoad trips, accommodation is usually locally owned such as hotels, apartments, guesthouses, and hostels, aiming to reflect local culture and support the local economy. The specifics about whether you will have a private bathroom will be shared by your Group Leader 2-5 days before departure alon'
- **gpt-4.1-mini · index** · `faq-ecuador-money` turn 1 (run 1): expected FAQ 'Which currency is used in Ecuador?', got ['Which currency is used in Peru?']
  - reply: "I don't have specific information about currency exchange in Ecuador from WeRoad's FAQs. You can find more in WeRoad's help centre or contact WeRoad support. Is there anything else you'd like to know about the trip to Ecuador?"
- **gpt-4.1-mini · index** · `faq-ecuador-money` turn 1 (run 2): expected FAQ 'Which currency is used in Ecuador?', got ['Which currency is used in Peru?']
  - reply: "I don't have information specifically about Ecuador's currency in WeRoad's FAQs, but I can tell you that Peru uses the Peruvian Sol (PEN). For Ecuador, you might want to check WeRoad's help centre or contact their support for details about currency and money exchange."
- **gpt-4.1-mini · index** · `faq-ecuador-money` turn 1 (run 3): expected FAQ 'Which currency is used in Ecuador?', got ['Which currency is used in Peru?']
  - reply: "I don't have specific information about Ecuador's currency in WeRoad's FAQs. You can find more in WeRoad's help centre or contact WeRoad support. If you want, I can help with other questions or with finding a trip!"
- **gpt-4.1-mini · index** · `faq-ecuador-money` turn 1 (run 4): expected FAQ 'Which currency is used in Ecuador?', got ['Which currency is used in Peru?']
  - reply: "I don't have information about the currency in Ecuador in the FAQs. You can find more in WeRoad's help centre or contact WeRoad support."
- **gpt-4.1-mini · index** · `faq-ecuador-money` turn 1 (run 5): expected FAQ 'Which currency is used in Ecuador?', got ['Which currency is used in Peru?']
  - reply: "I don't have specific information about currency exchange in Ecuador in WeRoad's FAQs. You can find more in WeRoad's help centre or contact WeRoad support for detailed advice on changing money there."
- **gpt-4.1-mini · index** · `faq-near-morocco-plugs` turn 1 (run 4): no FAQ answers this, but the reply doesn't say so
  - reply: "In Morocco, the type of plugs used is not directly mentioned in the FAQs I have. However, I suggest you bring a universal adapter to stay connected without any hassle, as this is a common recommendation for travel. If you'd like, I can help you find trips to Morocco now. Would you like that?"
- **gpt-4.1-mini · index** · `faq-near-mexico-tips` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: "The FAQs don't include specific information about tipping in Mexico. You can find more in WeRoad's help centre or contact WeRoad support for details. Can I help you find a trip to Mexico or elsewhere?"
- **gpt-4.1-mini · index** · `faq-near-mexico-tips` turn 1 (run 4): no FAQ answers this, but the reply doesn't say so
  - reply: "In Mexico, tipping is customary and appreciated for good service, although the exact amount isn't specified in WeRoad's FAQs. For reliable internet, it's recommended to buy a local SIM card as Wi-Fi availability can vary. If you want tips on the typical tipping amounts or other details, I suggest ch"
- **gpt-4.1-mini · embeddings** · `cheapest-first` turn 1 (run 4): trip 'Rainforest, White Sand & the Bioluminescent Bay' does not exist
  - reply: 'The cheapest trips in America start from €1169 for a 9-day trip to Puerto Rico: "Rainforest, White Sand & the Bioluminescent Bay." After that, there\'s a 10-day expedition in the Dominican Republic from €1229, and a 6-day New York city discovery from €1239. Would you like more details on any of these'
- **gpt-4.1-mini · embeddings** · `faq-plane-tickets` turn 1 (run 2): expected FAQ 'Are flights included?', got ["Can I find out my travel groups' flights?", 'Will I be sharing a room?', 'Can I see who’s in the group before I book the trip?']
  - reply: "You do need to book your own plane tickets for a WeRoad trip. You can share your flight details with your travel group in your personal area after booking, and see others' flight info too. This makes it easier to coordinate with your group. If you want to know more, your Travel Coordinator and group"
- **gpt-4.1-mini · embeddings** · `faq-plane-tickets` turn 1 (run 4): expected FAQ 'Are flights included?', got ["Can I find out my travel groups' flights?", 'Will I be sharing a room?', 'Can I cancel my booking?']
  - reply: "You don't need to book your own plane tickets separately through WeRoad. After booking your trip, you can add your flight details in your personal area, and see other group members' flights anonymously. You can coordinate flights with your travel group and ask your Travel Coordinator for help if nee"
- **gpt-4.1-mini · embeddings** · `faq-where-we-sleep` turn 1 (run 1): expected FAQ 'What type of accommodation should I expect on your trips?', got ['Will I be sharing a room?', 'How can I be part of the WeRoad community?', 'Can I cancel my booking?']
  - reply: 'On all WeRoad trips, you will share a room with other group members, which can be twins, triples, quadruples, or multi-share rooms. The bathroom may be private or shared with other travelers on the trip. Sometimes the accommodation might be tents, homestays, or camping for more adventurous experienc'
- **gpt-4.1-mini · embeddings** · `faq-it-share-room` turn 1 (run 2): trip 'Camera Privata' does not exist
  - reply: 'Sì, in tutti i nostri viaggi condividerai la camera con altri partecipanti del gruppo WeRoad. Il bagno potrà essere privato o condiviso solo con gli altri viaggiatori del viaggio. La condivisione può essere in camere doppie, triple, quadruple o in camere da più persone (fino a 8 in casi eccezionali)'
- **gpt-4.1-mini · embeddings** · `faq-two-questions` turn 2 (run 3): did not call get_faqs; expected FAQ 'Can I cancel my booking?', got no FAQ
  - reply: "Yes, you can cancel your booking on your own from MyWeRoad. If the tour is confirmed, amounts paid are non-refundable, but you can move your booking to another trip free of charge up to 31 days before departure. If the tour is not confirmed yet, canceling will refund everything you've paid (excludin"
- **gpt-4.1-mini · embeddings** · `faq-two-questions` turn 2 (run 4): did not call get_faqs; expected FAQ 'Can I cancel my booking?', got no FAQ
  - reply: 'Yes, you can cancel your booking through MyWeRoad. If the tour is confirmed, amounts paid are generally non-refundable, but you can move your booking to another trip free of charge up to 31 days before departure. If the tour is not confirmed, you get a full refund of what you paid (excluding Flexibl'
- **gpt-4.1-mini · embeddings** · `vague-recharge-in-europe` turn 1 (run 5): moods.relax: got None, expected {'min': 30}
  - reply: 'I found some relaxing options in Europe without partying: "Strasbourg and Colmar Express" with Christmas markets and fine wines in France, "Copenhagen Weekend" with Danish Hygge charm, or "Athens Weekend" visiting the Acropolis in Greece. Would you like trips of a specific duration or budget?'
