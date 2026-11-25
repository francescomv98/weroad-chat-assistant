"""The evaluation's own checks: a wrong metric is worse than no metric."""
import json
from pathlib import Path
from app.data import get_catalog
from evals import checks

BEFORE = {"continents": ["Asia"], "max_price": None, "must_have": [], "moods": {"party": None, "culture": None}, "sort": "relevance"}


def test_state_check_counts_right_wrong_and_unasked_changes():
    after = {**BEFORE, "max_price": 1500, "must_have": ["beach"], "sort": "price", "moods": {"party": 70, "culture": None}}
    expect = {"max_price": 1500, "must_have": {"contains": "cook"}, "continents": ["Asia"], "moods.party": {"min": 60}}

    result = checks.check_state(BEFORE, after, expect, allow=["sort"])

    # max_price and party are right (tp=2); must_have changed to the wrong value (fp=1, fn=1);
    # sort changed but is allowed; continents was kept, which is correct but not a "change".
    assert (result.tp, result.fp, result.fn) == (2, 1, 1)
    assert not result.ok
    assert result.problems == ["must_have: got ['beach'], expected {'contains': 'cook'}"]


def test_unasked_change_is_a_mistake():
    after = {**BEFORE, "continents": []}
    result = checks.check_state(BEFORE, after, {"max_price": None})
    assert result.fp == 1 and not result.ok
    assert "continents: changed without being asked" in result.problems[0]


def test_invented_prices_and_trips():
    names = checks.trip_names(["Bali 360°: Seminyak and Ubud", "Japan 360°: Tokyo", "Iceland: Northern Lights"])
    assert names == ["Bali 360°", "Japan 360°"]
    grounded = checks.readable([json.dumps({"title": "Bali 360°: Seminyak", "from_price_eur": 879})])

    ok = "Bali 360° starts at €879, within your 1,000 euros."
    assert checks.invented_facts(ok, grounded, "under 1000 euros", names) == []
    bad = "Japan 360° is only 650€!"
    assert checks.invented_facts(bad, grounded, "", names) == [
        "price €650 not returned by any tool", "trip 'Japan 360°' not returned by any tool"
    ]


def test_zero_results_reply_must_point_to_something_concrete():
    search = {"relaxations": [{"change": "budget up to €1035 (+15%)"}], "closest": [{"title": "Bali 360°: Ubud", "from_price_eur": 879}]}
    names = ["Bali 360°"]
    assert checks.offers_alternative("With a budget of €1,035 there are options.", search, names)
    assert checks.offers_alternative("Bali 360° is the closest match.", search, names)
    assert not checks.offers_alternative("Sorry, nothing found.", search, names)


def test_zero_results_counts_how_many_trips_a_suggestion_brings_back():
    # A real gpt-4.1-mini reply that the first version of the check wrongly failed.
    search = {"relaxations": [{"change": "any travel type", "result_count": 17},
                              {"change": "no budget limit", "result_count": 3}], "closest": []}
    reply = ("There are no trips with Northern Lights for under 800 euros. Removing the Northern Lights "
             "requirement yields 17 trips under 800 euros. If the budget is increased, there are 3 trips.")
    assert checks.offers_alternative(reply, search, [])
    # Numbers only count as whole numbers: "3" must not match inside a date like 2030.
    assert not checks.offers_alternative("Nothing until 2030, sorry.", search, [])



def test_zero_results_recognises_close_trips_by_their_place():
    # Real gpt-4.1-mini reply, wrongly failed before: it names the trips by city.
    search = {"relaxations": [], "closest": [{"title": "Athens Weekend: Acropolis, Cape Sounion", "from_price_eur": 339},
                                             {"title": "Budapest Weekend: The Pearl of the East", "from_price_eur": 329}]}
    reply = "No 3-day snorkelling trips, but consider Athens (Greece) or Budapest. Drop the snorkelling?"
    assert checks.offers_alternative(reply, search, [])
    assert not checks.offers_alternative("No 3-day snorkelling trips, sorry.", search, [])


def test_zero_results_recognises_close_trips_by_their_country():
    # Real gpt-4.1-mini reply that still failed after the city fix: it names countries.
    search = {"relaxations": [], "closest": [{"title": "Athens Weekend: Acropolis", "destination": "Greece"},
                                             {"title": "Copenhagen Weekend: Hygge", "destination": "Denmark"}]}
    reply = "The closest options are 3-day weekend trips in Greece, Denmark and Hungary, without snorkelling."
    assert checks.offers_alternative(reply, search, [])


def test_changing_the_order_is_never_a_mistake_unless_a_sort_is_expected():
    after = {**BEFORE, "max_price": 800, "sort": "price"}
    assert checks.check_state(BEFORE, after, {"max_price": 800}).ok
    assert not checks.check_state(BEFORE, after, {"max_price": 800, "sort": "rating"}).ok

def test_any_of_several_right_answers_is_accepted():
    after = {**BEFORE, "must_have": ["northern lights"]}
    alternatives = [{"travel_types": {"contains": "Northern Lights"}}, {"must_have": {"contains": "northern light"}}]
    result = checks.check_state_any(BEFORE, after, alternatives, allow=["travel_types", "must_have"])
    assert result.ok and result.tp == 1


def test_percentile_and_f1():
    assert checks.percentile([100, 200, 300, 400], 50) == 200
    assert checks.percentile(list(range(1, 101)), 99) == 99
    assert checks.prf(8, 2, 0) == (0.8, 1.0, 0.888888888888889)
    assert checks.prf(0, 3, 2) == (0.0, 0.0, 0.0)


def test_scenarios_only_use_real_values():
    """A typo in scenarios.json would silently make a scenario impossible to pass."""
    catalog = get_catalog()
    scenarios = json.loads(Path("evals/scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    assert len({s["id"] for s in scenarios}) == len(scenarios)
    for s in scenarios:
        for turn in s["turns"]:
            blocks = turn.get("expect_any") or [turn.get("expect", {})]
            for name, spec in [item for block in blocks for item in block.items()]:
                if name in ("continents", "destinations") and isinstance(spec, list):
                    pool = catalog.continents if name == "continents" else catalog.destinations
                    assert set(spec) <= set(pool), (s["id"], spec)
                if name == "travel_types" and isinstance(spec, dict) and "contains" in spec:
                    assert any(spec["contains"].lower() in t.lower() for t in catalog.travel_types), (s["id"], spec)
            faq_ids = {f.id for f in catalog.faqs}
            assert set(turn.get("faq", {}).get("ids", [])) <= faq_ids, (s["id"], turn["faq"])


def test_made_up_trips_are_caught_but_real_titles_and_labels_are_not():
    catalog = get_catalog()
    names = checks.trip_names([t.title for t in catalog.trips])
    catalog_text = " ".join([t.search_blob for t in catalog.trips] + catalog.travel_types + catalog.destinations)

    # Real gpt-4o-mini reply: these trips don't exist.
    invented = ("Here are the three trips:\n1. **Gastronomic Adventure in Italy**: hands-on cooking classes.\n"
                "2. **Culinary Journey in Thailand**: street food tours.")
    assert checks.made_up_titles(invented, "", names, catalog_text) == [
        "Gastronomic Adventure in Italy", "Culinary Journey in Thailand"
    ]

    # Real titles (even shortened), labels, dates and travel types are fine.
    fine = ('1. **Egypt 360°: Pyramids of Giza, Night Train to Aswan & the Red Sea**\n'
            '   - **Starting Price**: €1049\n   - **Next Departures**: **December 2 to December 10, 2026**\n'
            'The closest is "Transylvania Express", or a **Northern Lights** trip like **Bali 360° with a cooking class**.')
    assert checks.made_up_titles(fine, "", names, catalog_text) == []


def test_a_real_title_with_a_spelling_fix_is_not_made_up():
    """Real gpt-4.1-mini reply: the data spells it "Bioluminiscent bay"."""
    catalog = get_catalog()
    titles = [t.title for t in catalog.trips]
    catalog_text = " ".join(t.search_blob for t in catalog.trips)
    reply = 'The cheapest is a 9-day trip to Puerto Rico: "Rainforest, White Sand & the Bioluminescent Bay."'

    assert checks.made_up_titles(reply, "", [], catalog_text, titles) == []
    assert checks.made_up_titles('"Gastronomic Adventure in Italy"', "", [], catalog_text, titles) == ["Gastronomic Adventure in Italy"]


def test_faq_answers_are_not_checked_for_trip_titles():
    assert checks.faq_only(["search_faqs"]) and checks.faq_only(["get_faqs"])
    assert not checks.faq_only(["search_faqs", "update_search"]) and not checks.faq_only([])



def test_faq_retrieval_is_judged_on_the_faqs_returned():
    titles = {1: "Are flights included?", 8: "Can I get a refund if I cancel?", 4: "Can I cancel my booking?"}
    returned = checks.faq_titles_returned([json.dumps({"faqs": [{"title": "Can I cancel my booking?"}]}),
                                           json.dumps({"result_count": 3})])  # other tools are ignored
    assert returned == ["Can I cancel my booking?"]

    assert checks.check_faq({"ids": [8, 4]}, returned, "...", titles) == (True, None, [])
    found, _, problems = checks.check_faq({"ids": [1]}, returned, "...", titles)
    assert not found and problems == ["expected FAQ 'Are flights included?', got ['Can I cancel my booking?']"]
    assert checks.check_faq(None, returned, "...", titles) == (None, None, [])


def test_questions_no_faq_answers_must_be_admitted():
    no_answer = {"none": True}
    assert checks.check_faq(no_answer, [], "I don’t have information about visas for India.", {})[1]
    assert checks.check_faq(no_answer, [], "Non ho trovato informazioni sui visti.", {})[1]
    # Making up a policy is exactly what this check is for.
    assert not checks.check_faq(no_answer, [], "Yes, you need an e-visa, it costs $25.", {})[1]


def test_real_replies_that_admit_the_faqs_dont_cover_it():
    # The four gpt-4.1-mini replies the first version of the check wrongly failed.
    replies = [
        "I found info about internet but not specifically about tap water safety in Mexico in WeRoad's FAQs.",
        "The FAQ doesn't mention tap water safety in Mexico.",
        "I didn't find specific information about visa requirements for India in our FAQs.",
        "I found information about the plugs used in Japan but not specific weather details.",
        "I found information about tipping in Morocco, but nothing specific about plugs.",
        "WeRoad's FAQs do not explicitly mention travel insurance requirements.",
        "I found information about the type of plugs used in Japan, but not on the weather.",
        "In Morocco, the answer about plugs is not in the FAQ I accessed.",
        "The FAQs do not specify if dogs are allowed on WeRoad trips.",
        "The FAQs don't include specific information about tipping in Mexico.",
        "I found information on payment methods and currency in India, but not specifically on visa requirements.",
    ]
    assert all(checks.check_faq({"none": True}, [], r, {})[1] for r in replies)


def test_search_faqs_counts_as_the_faq_tool():
    assert checks.check_tools(["search_faqs"], {"must": ["get_faqs"], "must_not": ["update_search"]}) == []


def test_a_mood_minimum_of_zero_counts_as_not_set():
    """Real gpt-4.1-mini turn: it cleared moods it had set to 0, which changes no result."""
    zeros = {"moods": {"party": 0, "relax": 0, "nature": 0, "culture": 0, "history": 0}}
    after = {"moods": {"party": None, "relax": None, "nature": None, "culture": None, "history": None},
             "physical_ratings": ["LOW"]}

    result = checks.check_state(zeros, after, {"physical_ratings": {"contains": "LOW"}})

    assert result.ok, result.problems
    assert not checks.check_state({"moods": {"party": 60}}, {"moods": {"party": None}}, {}).ok


def test_the_eval_verdicts_become_langfuse_scores(monkeypatch):
    from evals import run as eval_run

    sent = []
    monkeypatch.setattr(eval_run.tracing, "score", lambda trace_id, name, value, comment=None: sent.append((name, value, comment)))
    rec = {"trace_id": "t1", "correct": False, "problems": ["max_price: got None"], "tools_ok": True, "invented": [],
           "has_expect": True, "state_ok": False, "zero_ok": None, "faq_found": True, "faq_admitted": None}

    eval_run.send_scores(rec)
    eval_run.send_scores({**rec, "trace_id": None})  # without --langfuse there is no trace: nothing is sent

    assert sent == [("correct", False, "max_price: got None"), ("tools_ok", True, None), ("grounded", True, None),
                    ("state_ok", False, None), ("faq_found", True, None)]
