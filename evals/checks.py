from __future__ import annotations
import json
import math
import re
from dataclasses import dataclass, field

# Changes that never remove a result: an internal detail of the text filter, and the order.
# A scenario that expects a specific sort ("cheapest first") still checks it.
ALWAYS_ALLOWED = {"text_match", "sort"}


# STATE

def flatten(state: dict) -> dict:
    """SearchState as flat fields; each mood becomes its own field (moods.party...)."""
    out = {}
    for key, value in state.items():
        if key == "moods":
            for mood, score in (value or {}).items():
                out[f"moods.{mood}"] = score
        else:
            out[key] = value
            
    return out


def _empty(value) -> bool:
    return value is None or value == [] or value == ""


def _norm(value):
    if isinstance(value, list):
        return sorted(str(v).lower() for v in value)
    if isinstance(value, str):
        return value.lower()
    
    return value


def _same(a, b) -> bool:
    return (_empty(a) and _empty(b)) or _norm(a) == _norm(b)


def match(value, spec) -> bool:
    """Does a state value satisfy an expectation from scenarios.json?"""
    if not isinstance(spec, dict):
        return _same(value, spec)
    
    items = [str(v).lower() for v in value] if isinstance(value, list) else []

    for op, arg in spec.items():
        wanted = [a.lower() for a in (arg if isinstance(arg, list) else [arg])] if op in ("contains", "excludes") else None
        if op == "contains" and not all(any(w in i for i in items) for w in wanted):
            return False
        if op == "excludes" and any(w in i for w in wanted for i in items):
            return False
        if op == "min" and (value is None or value < arg):
            return False
        if op == "max" and (value is None or value > arg):
            return False
        if op not in ("contains", "excludes", "min", "max"):
            raise ValueError(f"unknown matcher {op!r}")
        
    return True


@dataclass
class StateCheck:
    ok: bool
    tp: int  
    fp: int  
    fn: int 
    problems: list[str] = field(default_factory=list)


def check_state(before: dict, after: dict, expect: dict, allow=()) -> StateCheck:
    b, a = flatten(before), flatten(after)
    changed = {k for k in set(a) | set(b) if not _same(a.get(k), b.get(k))}
    allowed = set(allow) | ALWAYS_ALLOWED
    tp = fp = fn = 0
    problems = []

    for name, spec in expect.items():
        if match(a.get(name), spec):
            tp += name in changed
        else:
            fn += 1
            fp += name in changed
            problems.append(f"{name}: got {a.get(name)!r}, expected {spec!r}")

    for name in sorted(changed - set(expect)):
        if name in allowed or name.split(".")[0] in allowed:
            continue
        fp += 1
        problems.append(f"{name}: changed without being asked ({b.get(name)!r} -> {a.get(name)!r})")

    return StateCheck(not problems, tp, fp, fn, problems)


def check_state_any(before: dict, after: dict, alternatives: list[dict], allow=()) -> StateCheck:
    """Several answers can be equally right (e.g. 'northern lights' as a travel type or as a
    must-have keyword): score against the alternative the model got closest to."""
    results = [check_state(before, after, expect, allow) for expect in alternatives]
    return min(results, key=lambda r: (not r.ok, len(r.problems), r.fp + r.fn))


# TOOLS

def check_tools(called: list[str], spec: dict) -> list[str]:
    problems = [f"did not call {t}" for t in spec.get("must", []) if t not in called]
    problems += [f"called {t}" for t in spec.get("must_not", []) if t in called]
    max_calls = spec.get("max_calls", 4)

    if len(called) > max_calls:
        problems.append(f"{len(called)} tool calls (max {max_calls})")

    return problems


# REPLY

PRICE_RE = re.compile(r"(?:€|\beur(?:os?)?\b)\s*(\d[\d.,]*)|(\d[\d.,]*)\s*(?:€|\beur(?:os?)?\b)", re.I)


def _to_int(raw: str) -> int:
    raw = re.sub(r"(?<=\d)[.,](?=\d{3}(?:\D|$))", "", raw) 

    return int(re.split(r"[.,]", raw)[0])


def prices_in(text: str) -> set[int]:
    return {_to_int(m.group(1) or m.group(2)) for m in PRICE_RE.finditer(text)}


def trip_names(titles: list[str]) -> list[str]:
    """Short names the model uses for trips: 'Bali 360°' from 'Bali 360°: Seminyak, ...'.
    One-word names ('Iceland') are skipped: they're also country names."""
    names = {t.split(":")[0].strip() for t in titles}

    return sorted(n for n in names if len(n.split()) >= 2)


def readable(tool_outputs: list[str]) -> str:
    """Tool results as plain text (they are stored as ASCII-escaped JSON)."""
    out = []
    for content in tool_outputs:
        try:
            out.append(json.dumps(json.loads(content), ensure_ascii=False))
        except (TypeError, ValueError):
            out.append(str(content))

    return " ".join(out)


def invented_facts(reply: str, grounded: str, user_text: str, names: list[str], catalog_text: str = "") -> list[str]:
    """Prices and trip names in the reply that no tool returned (and the user didn't say),
    plus made-up trips: titles that don't exist anywhere in the catalog."""
    known_numbers = {int(n) for n in re.findall(r"\d+", grounded + " " + user_text)}
    problems = [f"price €{p} not returned by any tool" for p in sorted(prices_in(reply)) if p not in known_numbers]
    low_reply, low_grounded = reply.lower(), grounded.lower()
    problems += [f"trip '{n}' not returned by any tool" for n in names if n.lower() in low_reply and n.lower() not in low_grounded]
    if catalog_text:
        problems += [f"trip '{t}' does not exist" for t in made_up_titles(reply, grounded + " " + user_text, names, catalog_text)]

    return problems


# What a model presents as a trip name: **bold** text or "quoted" text.
TITLE_CANDIDATE_RE = re.compile(r"\*\*(.+?)\*\*|\"([^\"\n]{3,150})\"|“([^”\n]{3,150})”")
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"}
SMALL_WORDS = {"a", "an", "and", "the", "of", "in", "on", "to", "for", "with", "at", "by", "from", "&"}


# Words of the labels models put in bold before a value: "**Starting Price**: €879",
# "**Next Departures**: ...". A title made only of these words is a label, not a trip.
LABEL_WORDS = {"price", "prices", "starting", "next", "departure", "departures", "duration", "rating",
               "dates", "date", "days", "length", "cost", "seats", "availability", "highlights",
               "itinerary", "included", "includes", "destination", "trip", "details", "total",
               "available", "upcoming", "option", "options", "why", "best", "for", "you", "per", "person"}


def _is_label(text: str) -> bool:
    words = [w.lower() for w in re.findall(r"[^\W\d_]+", text)]
    return bool(words) and all(w in LABEL_WORDS or w in SMALL_WORDS for w in words)


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("’", "'"))


def _looks_like_title(text: str) -> bool:
    """'Gastronomic Adventure in Italy' yes; '**Duration:**', '**from €879**',
    '**December 2 to 10**' or '**no trips**' no."""
    if text.endswith(":") or "€" in text or "$" in text:
        return False
    words = re.findall(r"[^\W\d_][\w'’°-]*", text)
    if any(w.lower() in MONTHS for w in words):
        return False
    capitalised = [w for w in words if w[0].isupper()]
    content = [w for w in words if w.lower() not in SMALL_WORDS]
    return len(capitalised) >= 2 and len(capitalised) >= 0.6 * len(content)


def made_up_titles(reply: str, known_text: str, names: list[str], catalog_text: str) -> list[str]:
    """Trip-like titles in the reply that appear nowhere: not in the tool results, not in
    what the user wrote, not in the catalog (titles, descriptions, itineraries, types)."""
    haystack = _norm_text(known_text + " " + catalog_text)
    out = []
    for m in TITLE_CANDIDATE_RE.finditer(reply):
        candidate = next(g for g in m.groups() if g).strip().rstrip(".!?,")
        if _is_label(candidate) or not _looks_like_title(candidate):
            continue
        name = candidate.split(":")[0].strip()  # "Bali 360°: Seminyak, ..." -> "Bali 360°"
        if _norm_text(name) in haystack or any(n.lower() in candidate.lower() for n in names):
            continue
        out.append(candidate)
    return out


def faq_titles_returned(tool_outputs: list[str]) -> list[str]:
    """Titles of the FAQs the FAQ tool returned (in one turn)."""
    titles = []
    for content in tool_outputs:
        try:
            data = json.loads(content)
        except (TypeError, ValueError):
            continue
        if isinstance(data, dict):
            titles += [f.get("title", "") for f in data.get("faqs", [])]
    return titles


# Ways a reply admits the FAQs don't cover a question (English and Italian).
NO_ANSWER_MARKERS = (
    "don't have", "do not have", "couldn't find", "could not find", "can't find", "no information",
    "not sure", "don't know", "unable to find", "not covered", "isn't covered", "no specific",
    "not able to find", "doesn't cover", "does not cover", "non ho", "non trovo", "non so",
    "non ho trovato", "nessuna informazione",
    # Seen in real gpt-4.1-mini replies: "I didn't find specific information...", "The FAQ doesn't mention...",
    # "...but not specifically about tap water".
    "didn't find", "did not find", "doesn't mention", "does not mention", "not specifically",
    "not mentioned", "no faq", "non è presente", "non ci sono informazioni",
)


def check_faq(spec: dict | None, returned: list[str], reply: str, titles_by_id: dict[int, str]):
    """FAQ retrieval: did the tool return one of the expected FAQs in this turn?
    For questions no FAQ answers: does the reply say so instead of making up a policy?
    Returns (found, admitted, problems); None where the check doesn't apply."""
    if not spec:
        return None, None, []
    found = admitted = None
    problems = []
    if "ids" in spec:
        wanted = [titles_by_id[i] for i in spec["ids"]]
        found = any(t in returned for t in wanted)
        if not found:
            problems.append(f"expected FAQ {wanted[0]!r}, got {returned or 'no FAQ'}")
    if spec.get("none"):
        admitted = any(m in reply.lower().replace("’", "'") for m in NO_ANSWER_MARKERS)
        if not admitted:
            problems.append("no FAQ answers this, but the reply doesn't say so")
    return found, admitted, problems


def offers_alternative(reply: str, last_search: dict, names: list[str]) -> bool:
    """On zero results, the reply must point to something concrete: a close trip
    or one of the suggested changes, recognised by its numbers: the new budget, or
    how many trips it brings back ("3 trips if you remove the budget")."""
    low = reply.lower()
    close = " ".join(t.get("title", "") for t in last_search.get("closest", [])).lower()
    if any(n.lower() in low and n.lower() in close for n in names):
        return True
    # Models usually name a close trip by its place: "Athens" for "Athens Weekend: Acropolis...".
    # ...or by country: "Greece" for the same trip.
    closest = last_search.get("closest", [])
    places = {t.get("title", "").split()[0].strip(":,").lower() for t in closest if t.get("title")}
    places |= {t.get("destination", "").lower() for t in closest if t.get("destination")}
    if any(len(p) >= 4 and re.search(rf"\b{re.escape(p)}\b", low) for p in places):
        return True

    suggestion_numbers = set()
    for r in last_search.get("relaxations", []):
        suggestion_numbers |= {int(n) for n in re.findall(r"\d+", r.get("change", "")) if int(n) >= 10}
    suggestion_numbers |= {t.get("from_price_eur") for t in last_search.get("closest", [])}
    suggestion_numbers |= {r.get("result_count") for r in last_search.get("relaxations", [])}
    suggestion_numbers.discard(None)

    whole_numbers = {int(n) for n in re.findall(r"(?<![\d.,])\d+(?![\d.,]\d)", reply)}
    return bool((prices_in(reply) | whole_numbers) & suggestion_numbers)


# METRICS

def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile (no interpolation: with few samples p99 is the max)."""
    if not values:
        return None
    
    ordered = sorted(values)
    
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def prf(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if precision is None or recall is None:
        return precision, recall, None
    
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    
    return precision, recall, f1
