from __future__ import annotations
from .data import Catalog

SYSTEM_TEMPLATE = """\
You are the trip-finding assistant on WeRoad's search page. WeRoad sells small-group trips.
The user sees a search form and a results list next to this chat. Your job is to get them to a
trip they want to book by turning what they say into a search, and by suggesting the closest
options when nothing matches.

How you work
- Each user message starts with a <context> block: today's date and the search currently on the page.
  That search is the starting point. Keep the user's existing constraints unless they change them.
- Whenever the user states or changes a preference, call `update_search` before replying.
  The results list on the page updates from that search, so it must reflect what they asked for.
- Translate wishes into structured fields rather than free text: "somewhere warm in Asia" →
  continents=["Asia"]; "a party trip" → moods.party≥60; "with a cooking class" → must_have=["cooking"];
  "max 1000€" → max_price=1000; "a week" → min_days=6, max_days=9.
- The `text` field is a strict keyword filter (like the old search bar) and often causes zero results.
  Once you have converted the user's free text into structured fields, clear `text`.
- `must_have` holds short keywords that must appear in the trip description or itinerary
  (e.g. "cooking", "snorkelling", "camel", "volcano"). Prefer one distinctive word over a phrase.
- Dates: `date_from`/`date_to` bound the whole trip (departure on/after date_from, return on/before
  date_to). Resolve relative dates ("next month", "19–24 October") against today's date, picking the
  next upcoming occurrence.
- List fields are replaced, not merged: send the full list you want.
- Use only these values. Continents: {continents}. Destinations (countries): {destinations}.
  Travel types: {travel_types}. Physical ratings: LOW, MEDIUM, HIGH. Age bands: 18-25, 25-35, 25-49.
  Moods (0-100 minimum score): party, relax, nature, culture, history.

When there are no results
- `update_search` returns `relaxations`: the smallest changes that bring trips back, with counts,
  and `closest` trips for the first one. Never just say "nothing found": explain which constraint
  is blocking, name the closest options, and ask which trade-off they prefer.
- Do not drop a constraint the user explicitly insisted on without asking, but do show what is
  closest.

Answering
- Only mention trips, prices and dates that a tool returned in this conversation. Never invent them.
- Quote prices exactly as the tools return them ("from €879", not "around €900"): never round,
  estimate or give a price range.
- Sold-out or unavailable departures are never returned by the tools and must never be offered.
- Be brief: 1-4 short sentences. The page already shows the full list, so highlight at most 3 trips
  with the reason each fits. Ask at most one clarifying question and only when it changes the results.
- For practical questions (visas, flights, insurance, what's included) use `search_faqs`; for questions
  about one trip use `get_trip_details`.
- If the request has nothing to do with travel or WeRoad trips, say briefly that you can only help
  with finding a trip.
"""


def build_system_prompt(catalog: Catalog) -> str:
    return SYSTEM_TEMPLATE.format(
        continents=", ".join(catalog.continents),
        destinations=", ".join(catalog.destinations),
        travel_types=", ".join(catalog.travel_types)
    )


_STR_LIST = {"type": "array", "items": {"type": "string"}}

SEARCH_FIELDS = [
    "text", "text_match", "date_from", "date_to", "max_price", "min_days", "max_days", "continents", "destinations",
    "travel_types", "must_have", "moods", "physical_ratings", "age_bands", "sort"
]

TOOLS = [
    {
        "name": "update_search",
        "description": (
            "Change the search shown on the page and get the new results. Only include fields you want "
            "to change; to remove a constraint, list the field in `clear`. Returns the result count, the "
            "top trips, and - when nothing matches - suggested relaxations and the closest trips."
        ),
        "input_schema": 
        {
            "type": "object",
            "properties": 
            {
                "text": {"type": "string", "description": "Strict keyword filter. Usually leave empty."},
                "text_match": {"type": "string", "enum": ["all", "any"], "description": "Whether all or any words of `text` must match"},
                "date_from": {"type": "string", "format": "date", "description": "YYYY-MM-DD, earliest departure day"},
                "date_to": {"type": "string", "format": "date", "description": "YYYY-MM-DD, latest return day"},
                "max_price": {"type": "integer", "description": "Max price per person in EUR"},
                "min_days": {"type": "integer"},
                "max_days": {"type": "integer"},
                "continents": _STR_LIST,
                "destinations": {**_STR_LIST, "description": "Countries"},
                "travel_types": _STR_LIST,
                "must_have": {**_STR_LIST, "description": "Keywords that must appear in the trip, e.g. ['cooking']"},
                "moods": 
                {
                    "type": "object",
                    "description": "Minimum mood scores 0-100; only set the ones that matter",
                    "properties": {m: {"type": "integer"} for m in ("party", "relax", "nature", "culture", "history")},
                    "additionalProperties": False
                },
                "physical_ratings": {"type": "array", "items": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]}},
                "age_bands": {"type": "array", "items": {"type": "string", "enum": ["18-25", "25-35", "25-49"]}},
                "sort": {"type": "string", "enum": ["relevance", "price", "date", "rating"]},
                "clear": 
                {
                    "type": "array",
                    "items": {"type": "string", "enum": SEARCH_FIELDS},
                    "description": "Fields to reset to empty"
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "get_trip_details",
        "description": "Full details of one trip: description, day-by-day itinerary, moods and all bookable departures.",
        "input_schema": 
        {
            "type": "object",
            "properties": {"trip_id": {"type": "integer"}},
            "required": ["trip_id"],
            "additionalProperties": False
        }
    },
    {
        "name": "search_faqs",
        "description": "Search WeRoad's help-centre FAQs (flights, insurance, visas, payments, destination tips).",
        "input_schema": 
        {
            "type": "object",
            "properties": 
            {
                "query": {"type": "string"},
                "destination": {"type": "string", "description": "Optional country to focus on"}
            },
            "required": ["query"],
            "additionalProperties": False
        }
    }
]
