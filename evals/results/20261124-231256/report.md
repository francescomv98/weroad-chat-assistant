# Evaluation 2026-11-24 23:14

Scenarios: 19 · runs per scenario: 2 · workers: 1 · frozen today: 2026-11-24

| Metric | gpt-4.1-mini |
|---|---|
| Requests (turns) | 38 |
| Correct requests | 23/38 (61%) |
| Failed requests | 0/38 (0%) |
| Latency p50 | 1.76 s |
| Latency p95 | 2.47 s |
| Latency p99 | 2.60 s |
| Cost / turn | $0.00098 |
| Total cost | $0.03727 |
| Correct state (accuracy) | 12/12 (100%) |
| State fields precision | n/a |
| State fields recall | n/a |
| State fields F1 | n/a |
| Correct tool use | 32/38 (84%) |
| update_search precision | n/a |
| update_search recall | n/a |
| update_search F1 | n/a |
| Turns with invented facts (lower is better) | 0/38 (0%) |
| Zero results handled | n/a |
| FAQ found (retrieval) | 23/34 (68%) |
| No FAQ answer admitted | 0/4 (0%) |

## Correct requests by category

| Category | gpt-4.1-mini |
|---|---|
| faq | 6/6 (100%) |
| faq_destination | 5/6 (83%) |
| faq_italian | 1/6 (17%) |
| faq_no_answer | 0/4 (0%) |
| faq_paraphrase | 11/16 (69%) |

## What went wrong

- **gpt-4.1-mini** · `faq-plane-tickets` turn 1 (run 2): expected FAQ 'Are flights included?', got ["Can I find out my travel groups' flights?", 'Will I be sharing a room?', 'Do I need to tip in China?']
  - reply: "You do need to book your own plane tickets for WeRoad trips. After booking, you can add your flight details in your personal area on the website to share them anonymously with your travel group. If you want, you can also coordinate flights with your group through the trip's message space. Would you "
- **gpt-4.1-mini** · `faq-group-guide` turn 1 (run 1): did not call search_faqs; expected FAQ 'Who is the Travel Group Leader and what is their role on the trip?', got no FAQ
  - reply: "I can help you find trips, but I don't have specific information about the guides for each trip. If you'd like, I can provide details about a particular trip you're interested in. Just let me know which one!"
- **gpt-4.1-mini** · `faq-group-guide` turn 1 (run 2): did not call search_faqs; expected FAQ 'Who is the Travel Group Leader and what is their role on the trip?', got no FAQ
  - reply: "I can help you find trip guides' information for specific WeRoad trips. Could you please tell me which trip you're interested in or the destination? This will help me provide details about the group's guide."
- **gpt-4.1-mini** · `faq-where-we-sleep` turn 1 (run 1): did not call search_faqs; expected FAQ 'What type of accommodation should I expect on your trips?', got no FAQ
  - reply: 'WeRoad trips typically use a mix of accommodation types, often including hotels and hostels depending on the destination and trip style. If you want, I can check the details for a specific trip to see what accommodations are included. Would you like to look at a particular destination or type of tri'
- **gpt-4.1-mini** · `faq-where-we-sleep` turn 1 (run 2): did not call search_faqs; expected FAQ 'What type of accommodation should I expect on your trips?', got no FAQ
  - reply: "WeRoad trips typically include accommodation that fits the group's style, mainly small hotels, guesthouses, or boutique stays rather than hostels. For exact details about lodging on a specific trip, I can check the trip details for you if you name a particular trip or destination."
- **gpt-4.1-mini** · `faq-iceland-weather` turn 1 (run 2): did not call search_faqs; expected FAQ 'What’s the weather like in Iceland?', got no FAQ
  - reply: "The current search result is for a trip to Iceland, but the trip details I retrieved are for Italy Express: Naples and the Amalfi Coast, which doesn't apply to Iceland's weather.\n\nIceland can get quite cold, especially late autumn and winter, often ranging from near freezing to below freezing temper"
- **gpt-4.1-mini** · `faq-it-cancel` turn 1 (run 1): expected FAQ 'Can I get a refund if I cancel?', got no FAQ
  - reply: 'Non ho trovato informazioni specifiche sulle cancellazioni e rimborsi nelle FAQ. Ti consiglio di contattare direttamente il servizio clienti di WeRoad per assistenza su cancellazioni e politiche di rimborso. Posso aiutarti a trovare un viaggio se vuoi! Vuoi cercare qualcosa in particolare?'
- **gpt-4.1-mini** · `faq-it-cancel` turn 1 (run 2): did not call search_faqs; expected FAQ 'Can I get a refund if I cancel?', got no FAQ
  - reply: 'Posso aiutarti a trovare un viaggio, ma per domande su cancellazioni e rimborsi ti consiglio di consultare direttamente la sezione FAQ o contattare il servizio clienti WeRoad. Vuoi che ti mostri alcuni viaggi?'
- **gpt-4.1-mini** · `faq-it-flights` turn 1 (run 1): expected FAQ 'Are flights included?', got no FAQ
  - reply: "I voli non sono inclusi nel prezzo dei nostri viaggi; generalmente, il costo indicato copre solo il tour e l'accompagnamento. Vuoi che ti aiuti a trovare un viaggio con partenza vicina o con altre caratteristiche?"
- **gpt-4.1-mini** · `faq-it-flights` turn 1 (run 2): expected FAQ 'Are flights included?', got no FAQ
  - reply: 'I voli non sono inclusi nel prezzo dei nostri viaggi WeRoad; di solito sono da prenotare a parte. Vuoi che ti aiuti a trovare un viaggio e ti spiego come organizzare il volo?'
- **gpt-4.1-mini** · `faq-it-currency-peru` turn 1 (run 1): expected FAQ 'Which currency is used in Peru?', got no FAQ
  - reply: 'In Perù si usa il Nuevo Sol peruviano (PEN) come moneta ufficiale. Vuoi che ti aiuti a trovare un viaggio in Perù o altre informazioni per il tuo viaggio?'
- **gpt-4.1-mini** · `faq-none-tap-water` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: "I found info about internet but not specifically about tap water safety in Mexico in WeRoad's FAQs. Generally, it's recommended to avoid drinking tap water in Mexico and use bottled or filtered water instead for safety. Would you like me to show you trips to Mexico now?"
- **gpt-4.1-mini** · `faq-none-tap-water` turn 1 (run 2): no FAQ answers this, but the reply doesn't say so
  - reply: "The FAQ doesn't mention tap water safety in Mexico. Generally, it's recommended to avoid drinking tap water in Mexico and stick to bottled or purified water to avoid stomach issues. Would you like me to help you find trips to Mexico?"
- **gpt-4.1-mini** · `faq-none-visa-india` turn 1 (run 1): no FAQ answers this, but the reply doesn't say so
  - reply: "I didn't find specific information about visa requirements for India in our FAQs. Typically, visa needs depend on your nationality and length of stay, so I recommend checking the official government website or your local embassy for the most accurate and up-to-date information. Can I help you find t"
- **gpt-4.1-mini** · `faq-none-visa-india` turn 1 (run 2): no FAQ answers this, but the reply doesn't say so
  - reply: 'I found information on payment methods and currency in India, but not specifically on visa requirements. Generally, you do need a visa to travel to India, but the type and process depend on your nationality. Would you like me to check specific visa details for your nationality?'
