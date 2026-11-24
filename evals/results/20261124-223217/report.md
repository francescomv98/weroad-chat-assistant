# Evaluation 2026-11-24 22:38

Scenarios: 26 · runs per scenario: 2 · workers: 1 · frozen today: 2026-11-24

| Metric | gpt-4.1-mini | gpt-4o-mini |
|---|---|---|
| Requests (turns) | 58 | 58 |
| Correct requests | 58/58 (100%) | 45/58 (78%) |
| Failed requests | 0/58 (0%) | 0/58 (0%) |
| Latency p50 | 2.18 s | 3.75 s |
| Latency p95 | 2.76 s | 5.40 s |
| Latency p99 | 4.39 s | 5.86 s |
| Cost / turn | $0.00098 | $0.00045 |
| Total cost | $0.05660 | $0.02615 |
| Correct state (accuracy) | 58/58 (100%) | 49/58 (84%) |
| State fields precision | 100% | 90% |
| State fields recall | 100% | 90% |
| State fields F1 | 100% | 90% |
| Correct tool use | 58/58 (100%) | 53/58 (91%) |
| update_search precision | 100% | 100% |
| update_search recall | 100% | 98% |
| update_search F1 | 100% | 99% |
| Turns with invented facts (lower is better) | 0/58 (0%) | 0/58 (0%) |
| Zero results handled | 8/8 (100%) | 10/10 (100%) |

## Correct requests by category

| Category | gpt-4.1-mini | gpt-4o-mini |
|---|---|---|
| dates | 6/6 (100%) | 6/6 (100%) |
| faq | 6/6 (100%) | 2/6 (33%) |
| multi_turn | 12/12 (100%) | 9/12 (75%) |
| off_topic | 4/4 (100%) | 4/4 (100%) |
| refine | 22/22 (100%) | 20/22 (91%) |
| trip_details | 2/2 (100%) | 2/2 (100%) |
| zero_results | 6/6 (100%) | 2/6 (33%) |

## What went wrong

- **gpt-4o-mini** · `cooking-from-strict-text` turn 1 (run 1): must_have: got [], expected {'contains': 'cook'}; text: got 'cooking class', expected None; did not call update_search
  - reply: "Your current search for trips with a cooking class is already set to only show options that include this feature. Here are the three available trips you've found:\n\n1. **Gastronomic Adventure in Italy**: A delightful trip exploring Italian cuisine, including hands-on cooking classes.\n2. **Culinary Jo"
- **gpt-4o-mini** · `cooking-from-strict-text` turn 1 (run 2): text: got 'cooking class', expected None
  - reply: 'Here are the trips that include a cooking class:\n\n1. **Bali 360°: Seminyak, Ubud, Rice Terraces & a Balinese Cooking Class** in Indonesia, 8 days, from €879. Next departures: 02-09 January 2027 (€1039, 5 seats), 03-10 January 2027 (€939, 7 seats).\n\n2. **Costa Rica 360°: between jungle, beaches and v'
- **gpt-4o-mini** · `change-of-mind` turn 2 (run 1): continents: got [], expected ['America']
  - reply: 'Here are some cultural trip options for you:\n\n1. **Egypt 360°: Pyramids of Giza, Night Train to Aswan & the Red Sea**  \n   - **Duration:** 9 days  \n   - **Rating:** 5.0  \n   - **Price:** from €1049  \n   - **Next Departures:** December 2 to December 10, 2026 (€1049, 7 seats available)\n\n2. **Athens We'
- **gpt-4o-mini** · `money-is-not-a-problem` turn 1 (run 1): max_price: got 10000, expected None
  - reply: "I've updated your search to remove the budget limit, and there are now 13 options available in Asia. Here are three exciting trips you might consider:\n\n1. **Vietnam 360°: from Hanoi to Ho Chi Minh City** - A comprehensive 13-day adventure for €1549. Next departures include December 2 and January 5.\n"
- **gpt-4o-mini** · `money-is-not-a-problem` turn 1 (run 2): max_price: got 10000, expected None
  - reply: "Now that money isn't a concern, here are several exciting trips in Asia:\n\n1. **Vietnam 360°: from Hanoi to Ho Chi Minh City** - 13 days for €1549. It's highly rated at 5.0, with upcoming departures including one on December 2nd. \n\n2. **Kyrgyzstan 360°: Bishkek, Yurt Nights & Eagle Hunters of Central"
- **gpt-4o-mini** · `japan-under-900` turn 1 (run 1): continents: changed without being asked ([] -> ['Asia'])
  - reply: 'It looks like there are currently no trips to Japan for under €900. However, I can suggest some alternatives. \n\n1. **Bali 360°: Seminyak, Ubud, Rice Terraces & a Balinese Cooking Class** - An 8-day trip to Indonesia, priced from €879, departing on **January 20, 2027**.\n\n2. **Istanbul Express: From A'
- **gpt-4o-mini** · `japan-under-900` turn 1 (run 2): continents: changed without being asked ([] -> ['Asia'])
  - reply: "I found that there are currently no trips to Japan under €900. However, I can suggest a couple of alternatives in Asia that fit your budget.\n\n1. **Bali 360°: Seminyak, Ubud, Rice Terraces & a Balinese Cooking Class** in Indonesia for **from €879**. It's an 8-day trip and has a great rating of 4.9. N"
- **gpt-4o-mini** · `cheap-northern-lights` turn 1 (run 1): travel_types: got [], expected {'contains': 'Northern Lights'}; moods.nature: changed without being asked (None -> 70)
  - reply: 'It seems that no trips are currently available that match your request for northern lights under 800 euros. The specific constraint of needing "northern" is blocking the results. \n\nThe closest option is a trip titled **"Transylvania Express: On the road in the land of Count Dracula"** in Romania, wh'
- **gpt-4o-mini** · `cheap-northern-lights` turn 1 (run 2): moods.nature: changed without being asked (None -> 100)
  - reply: "It looks like there are currently no trips to see the Northern Lights for less than €800, mainly due to the strict nature mood preference you're looking for. However, there are several other interesting trips within your budget.\n\n1. **Athens Weekend: Acropolis, Cape Sounion and taverna nights** - Gr"
- **gpt-4o-mini** · `currency-in-peru` turn 1 (run 1): did not call search_faqs
  - reply: "I can only assist with finding a trip. For specific questions about currency or other details, please check WeRoad's FAQs. Would you like to refine your search for trips to Peru or explore other options?"
- **gpt-4o-mini** · `currency-in-peru` turn 1 (run 2): did not call search_faqs
  - reply: 'I can only help with finding trips. Would you like to explore the options for your trip to Peru?'
- **gpt-4o-mini** · `cancel-and-refund` turn 1 (run 1): did not call search_faqs
  - reply: 'I can only help with finding a trip. For questions like refunds, I recommend checking WeRoad’s help center or contacting their customer service directly. Let me know if you want assistance in finding a trip!'
- **gpt-4o-mini** · `cancel-and-refund` turn 1 (run 2): did not call search_faqs
  - reply: 'I can only help you find trips. For questions about cancellations and refunds, please check the WeRoad help center or look for their specific policies on their website. How can I assist you with planning your travel?'
