# Decisions

What I built, what I left out, and why. Numbers come from the eval runs committed in `evals/results/`.

## The problem I chose to solve

Users on the search page often don't know what they want yet and many text searches return nothing
even when matching trips exist. The core of the prototype is therefore **one loop**: the user says
what they want → the assistant turns it into a structured search → the results list on the page
updates → if nothing matches, the assistant explains what is blocking and proposes the closest options.

Built: search API, assistant with tools, zero-result relaxation, FAQ answers, a single-page UI, tests
and an LLM evaluation. Left out on purpose: auth, real integrations, booking, a polished UI, session
persistence, streaming (see "What I left out").

## Architecture

**One `SearchState` shared by the form and the assistant** (`app/models.py`). The assistant never
"talks about" a search it can't show: it changes the same object the form uses, and the page re-renders
from it. The user's current search (text, dates, filters) is the starting point of every turn.

**Business rules in code, the LLM only translates and explains.**

| Rule | Where | Why not in the prompt |
|---|---|---|
| Sold-out, full or past departures never shown | `Departure.is_bookable` | A requirement must hold 100% of the time, not 99% |
| Zero results → closest options | `app/relax.py` | Deterministic, testable, free, and every suggestion comes with a real result count |
| Past dates ("19–24 October" in November) moved to the next year | `Assistant._move_past_dates` | The eval caught the model searching last October and telling users there were no trips |

**Relaxation engine.** Each constraint has relaxation steps with a cost (e.g. dates ±7 days = 2,
budget +15% = 2, drop a must-have = 4, any destination = 8). It tries single steps cheapest-first, one
suggestion per field, max 3; if none works alone, it removes whole fields cheapest-first until trips come
back. The model receives the suggestions with their result counts and the closest trips, and asks the user
which trade-off they prefer instead of dropping a constraint they insisted on.

**Natural language → structured filters, not free text.** The old search bar's `text` is a strict
keyword filter (every word must match), which is what produces the zero-result searches. The prompt tells
the model to map wishes to fields (`"somewhere warm in Asia"` → `continents`, `"a party trip"` →
`moods.party ≥ 60`, `"with a cooking class"` → `must_have=["cooking"]`) and to clear `text`.

## AI stack

**Tools** (`app/prompts.py`): `update_search` (partial update + `clear`, returns count, top 5 trips and,
when empty, relaxations and closest trips), `get_trip_details`, and an FAQ tool. Tool results are small
and factual (`summarise_for_model`); invalid arguments go back to the model as an error so it can retry;
max 6 tool rounds per turn; on an exception the turn is rolled back from the session.

**Grounding.** The model may only mention trips, prices and dates a tool returned, quote prices exactly,
and answer practical questions only from FAQs. The eval checks invented prices and trip names on every turn.

**Model: Claude Haiku 5.5 at low effort** (`LLM_PROVIDER=anthropic`, default), gpt-4.1-mini as the
alternative (`LLM_PROVIDER=openai`). Both run behind the same `LLMClient` protocol (`app/llm.py`), so the
eval compares them on the same scenarios (`--models gpt-4.1-mini anthropic:claude-haiku-5-5@low`).

First choice, among OpenAI models (run `20261124-223217`, 26 scenarios × 2): gpt-4.1-mini, 58/58 correct
against 45/58 for gpt-4o-mini, which kept strict text filters, invented budget limits and refused FAQ
questions.

Then gpt-4.1-mini against Claude Haiku 5.5 (78 scenarios):

| | gpt-4.1-mini | Haiku 5.5 (medium) | Haiku 5.5 @low | **Haiku 5.5 @low + prompt fix** |
|---|---|---|---|---|
| Run | `20261125-144136` (×2) | `20261125-144136` (×2) | `20261125-150058` (×5) | `20261125-152811` (×2) |
| Correct requests | 170/172 | 172/172 | 423/430 | **172/172** |
| Real failures (read one by one) | 1 | 0 | 5 | **0** |
| Latency p50 / p95 / p99 | **2.05 / 2.74 / 3.75 s** | 2.16 / 3.89 / 5.59 s | 2.07 / 3.75 / 4.25 s | 2.00 / 3.66 / 4.39 s |
| Cost / turn | $0.00120 | $0.00053 | $0.00037 | **$0.00046** |

- **Quality is a tie.** gpt-4.1-mini's one real miss: "something adventurous" got no adventurous filter.
- **Haiku costs ~60% less per turn**, so it is the default. Low effort trims its thinking: cheaper and a
  shorter tail (p99 5.6 → 4.4 s) than the default medium effort.
- **Low effort brought one problem, fixed in the prompt.** With zero results it sometimes removed a filter
  the user had just asked for ("Japan under €900" → budget removed, a €2,629 trip shown), 5 turns in 430.
  The prompt now says to never remove or loosen a constraint to make results appear, but to keep the
  search and ask which trade-off the user prefers: the three affected scenarios went from 10/15 to 15/15
  (`20261125-152204`).
- **Style.** Haiku formatted ~half its replies as bullet lists with bold, against the prompt's "1-4 short
  sentences"; "plain sentences, no lists, headings or bold" brought that to 5/172.
- **Trade-off kept:** Haiku's slowest replies are ~1 s slower than gpt-4.1-mini's (p95 3.7 vs 2.7 s), from
  the thinking it does before answering. Streaming the reply would hide most of it.
- Embeddings for FAQ search stay on OpenAI (`text-embedding-3-small`) with either model.

**Prompt caching.** The system prompt and tools are built once and never change; per-turn data (today,
current search, result count) goes in a `<context>` block in the user message, so every request starts
with the same prefix. OpenAI caches it automatically; Anthropic caches only when asked, so every request
sets `cache_control`. Measured share of input tokens served from the cache (billed at 25% with gpt-4.1-mini, 10%
with Haiku 5.5): 50-85% with OpenAI, 70-88% with Haiku. The OpenAI share varies with OpenAI's load: an A/B
test in the same time window found no effect of `prompt_cache_key` (37 vs 34 of 80 calls missed the cache
entirely), so it stays off.

## Agent loop: custom, and how it maps to LangGraph

The loop is ~60 lines in `Assistant._turn`: call the model, run the tools it asks for, send the results
back, stop when it answers. In LangGraph terms:

| LangGraph | This code |
|---|---|
| State | `messages` + `SearchState` (already explicit and shared with the page) |
| Node `agent` | `self.llm.create(...)` |
| Node `tools` | `_run_tool`: `update_search`, `get_trip_details`, FAQ tool |
| Conditional edge | no tool calls → END; otherwise → `tools` → `agent` |
| Recursion limit | `max_tool_rounds = 6`, then a fallback reply |
| Checkpointing | `self.sessions` in memory, keyed by `session_id` (= LangGraph `thread_id`); a failed turn is rolled back. LangGraph: a memory/Postgres checkpointer |
| Human-in-the-loop | today a prompt rule ("ask before dropping a constraint the user insisted on"); LangGraph: an `interrupt` before applying a relaxation |

**Why custom.** One agent, three tools, one loop: a framework would add a dependency and a layer to debug
without removing code. Keeping the loop in hand gives full control over what matters here: a static
prompt prefix for caching, tool errors sent back to the model, per-turn logging (tokens, cost, latency,
tool arguments) and an eval harness that injects a fake LLM and a frozen date. This follows Anthropic's
"Building effective agents": start with plain API calls, add a framework when it pays for itself.

**When I'd move to LangGraph:** sessions that must survive restarts or last days (durable checkpoints),
real approval steps (interrupts), streaming intermediate steps to the UI, or several agents (search,
booking, support) with routing between them.

## Retrieval

### FAQs: three approaches measured

| Approach | Run | FAQ found | Notes |
|---|---|---|---|
| Keyword search (model writes a query) | `20261124-231256` | 68% | Italian 1/6; answered from general knowledge when search missed |
| **Index**: the model picks from the 50 titles in the tool description (~600 tokens, cached) | `20261124-232758` | 100% | Italian 6/6, correct requests 61% → 100% |
| **Embeddings**: model writes a self-contained English query, cosine similarity on `text-embedding-3-small` | `20261125-101958` | 98% | Searches title **and body** |

After adding 30 harder scenarios (answers only in the FAQ body, near misses like "weather in Japan" when
only Iceland/Denmark/... exist, Spanish/French/German, FAQs in the middle of a search), index vs
embeddings over 49 FAQ scenarios × 5 runs (`20261125-101958`, re-scored after the checker fix below):

| | Index | Embeddings |
|---|---|---|
| Correct requests (checker) | 257/265 (97.0%) | 259/265 (97.7%) |
| Real failures, after reading each one | 8 | **4** |
| Answer only in the FAQ body | 12/15 | **15/15** |
| Near miss (FAQ exists for another country) | 17/20 | **19/20** |
| "No FAQ answers this" admitted | 41/45 | **44/45** |
| Latency p50 | **1.79 s** | 2.09 s |
| Cost / turn | **$0.00082** | $0.00118 |

Real failures. Index: picks "accommodation" for "private bathroom?" (bathroom is only in the body of
"Will I be sharing a room?") 3/5; answers Japan plugs for "weather in Japan" or Greece plugs for Morocco
3×; makes up a no-dogs policy 1×; rounds a suggested budget to "around €2300" 1×. Embeddings: "do I need
to book my own plane tickets?" ranks "Can I find out my travel groups' flights?" above "Are flights
included?" 3/5 (once the reply even says the opposite of the FAQ); Morocco plug types from general
knowledge 1×. The 2 remaining embeddings "failures" are a checker artefact: the model answered a follow-up
from a FAQ it had already received in the previous turn.

**Decision: embeddings are the default (`FAQ_RETRIEVER=embeddings`), the index stays as an option.**
They fail half as often, mostly on the cases users actually phrase differently from the titles, and they
scale: the index grows the prompt with every FAQ, embeddings don't. The price is +0.3 s and +$0.0004 per
turn. Lessons that shaped the implementation:
- **A similarity threshold can't detect "no FAQ answers this".** "Visa for India" scores 0.42 against
  "Which currency is used in India?", real matches score 0.36–0.47. The cut-off (0.3) only drops noise;
  the prompt tells the model the closest FAQs may not answer and to say so.
- **The model rewrites the query** (English, self-contained, with the destination), so "what money do
  they use there?" with Peru on the page becomes "Which currency is used in Peru?".
- FAQ vectors are computed once per process, in memory, with plain-Python cosine similarity: no vector
  database for 50 documents. In production they'd be computed when FAQs change and stored (e.g. pgvector).
- **Generic words are removed from the query before embedding it.** The logged queries showed the cause of
  the plane-tickets miss: the model wrote "…plane tickets **for a WeRoad trip**?", and since every FAQ is
  about WeRoad trips those words pushed the right one down. "WeRoad" and "on the trip" are stripped in
  code (the tool description asks the same, but the model ignored it in 2/5 queries); on the 203 logged
  queries, right FAQ in the top 3 went from 200 to 203 (`6e1306d`).

### Trips: structured filters, no semantic search (for now)

A reviewer suggested testing vague requests: "I want to disconnect from work", "an authentic experience
away from tourist crowds", "adventurous but not physically demanding". The model maps them to the existing
fields (moods such as relax/nature/culture, `physical_ratings`, travel types) with relevant results, so I
didn't add embedding search over trips. They are now eval scenarios (`vague`: the three sentences, a
follow-up turn, Italian, and on top of an existing search; each must set a relevant filter and return
trips): 14/14 with Haiku 5.5 @low (`20261125-152811`). If those requests start failing, the next step is
hybrid retrieval: structured filters as hard constraints, embedding similarity on description/itinerary
to rank.

## How quality is measured

`evals/`: 78 scenarios on the real data with a frozen "today" (refine, dates, multi-turn, zero results,
vague requests, trip details, off-topic, 9 FAQ categories). **Deterministic checks, no LLM judge**: cheap, reproducible,
and every failure has an exact reason.

- State: accuracy and field-level precision/recall/F1 against the expected `SearchState`; changing a
  field the user didn't mention counts as a mistake.
- Tools: required/forbidden calls, `update_search` precision/recall.
- Reply: invented prices or trip names, zero results with a concrete alternative, FAQ found, "no FAQ"
  admitted.
- Latency p50/p95/p99 (after a warm-up call), cost per turn including cached tokens and embeddings,
  share of input tokens served from the prompt cache.
- Several models in one report, one column each: `--models gpt-4.1-mini anthropic:claude-haiku-5-5@low`.
- At least 2 runs per scenario (models aren't deterministic), 5 before choosing between options.

The checks are tested on real model replies (`tests/test_eval_checks.py`). I read the "What went wrong"
section of every report: false negatives (e.g. "not specific weather details" not recognised as admitting)
are fixed in the checker with the real reply added as a test, never by editing the scenario.

What the eval has already fixed:
- Past dates searched as last year, and rounded prices (`cab9e1b`).
- FAQ retrieval 68% → 100% by letting the model pick from the FAQ index (`a81e47a`), then FAQ index →
  embeddings, which also find answers that are only in the FAQ text (`3ad212f`).
- In `6e1306d`: the plane-tickets miss (generic words removed from the FAQ query); general knowledge added
  after FAQs that don't answer (the rule is repeated in every FAQ tool result, and one fixed "no FAQ"
  reply points to WeRoad's help centre); "around €2300" for a suggested €2298 (suggested budgets rounded
  up to €10 in `relax.py`); trekking mapped to a keyword instead of the travel type, and moods the user
  never asked for.
- With Haiku 5.5 at low effort: filters removed on zero results to make trips appear, and replies
  formatted as lists (`46696a0`).

The checker was fixed along the way too, always from a real reply: phrasings that do admit "no FAQ",
real titles with a spelling fix, follow-ups answered from a FAQ already returned, a mood
minimum of 0 counted as not set.

Tests (`pytest`, no API calls): search, relaxation, agent loop with a fake LLM (tool errors, round limit,
rollback), cost parsing, API, and integration tests on the real sample data.

## Observability (Langfuse)

Optional: with `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` set, the app sends one trace per chat turn to
Langfuse Cloud (EU), grouped in a session per conversation (`app/tracing.py`).

- **What a trace shows:** the turn (message in, reply out, search before/after, latency, tokens, cost),
  one `generation` per LLM call (model, effort, the conversation sent, the reply or tool calls, tokens
  including cached, cost) and one `tool` observation per tool call (arguments, result, ERROR if it failed).
- **Instrumented in the assistant, not in each provider's client**, so OpenAI and Claude turns look the
  same and can be compared side by side. Only these observations are exported: the Anthropic SDK traces
  its own calls with OpenTelemetry, which Langfuse picked up as a second, empty generation inside each of
  ours (found by reading the first eval traces back through the API).
- **For impact, not only debugging:** each trace is tagged with how the turn ended (`outcome:results`,
  `outcome:zero-results-with-suggestions`, `faq`, `no-tools`, `tool-error`) and with the code version
  (`release` = git commit), so dashboards count the metrics below on real traffic and compare them before
  and after a prompt or model change.
- **Linked to the eval:** `python -m evals.run --langfuse` sends the eval's turns to a separate `eval`
  environment, tagged by run, model and category, with the checks as scores (`correct` with the problems
  as comment, `state_ok`, `tools_ok`, `grounded`, `zero_results_handled`, `faq_found`, `faq_admitted`):
  filter `correct = 0` and every failure opens as its full trace. `report.md` stays the gate.
- **Off by default:** no keys, no tracing; tests never trace; a Langfuse failure never breaks a turn.
- **Not used on purpose:** Langfuse datasets/experiments (the eval harness does it, versioned in git) and
  prompt management (the prompt lives next to the code that depends on it, and must stay static for
  prompt caching).
- **Production notes:** chat text and model inputs are sent to Langfuse's EU servers, fine for demo
  data, a GDPR review for real users (masking, retention, or self-hosting); sampling at high volume.

## What I left out

| Left out | Why / what I'd do |
|---|---|
| Auth, booking, real WeRoad APIs | Not required; the assistant ends on the trip URL |
| Session persistence | Sessions live in memory; Redis or the DB in production |
| Streaming replies | p50 is ~2 s; streaming is the first UX improvement for production |
| Semantic search over trips | Filters handled the vague requests I tried (see above) |
| LLM-as-judge for reply quality | Deterministic checks first; a judge for tone/helpfulness would be next |
| Polished UI | One HTML page that shows the loop |

## What I'd ship first and how I'd measure it

Ship the assistant to a share of users (A/B), starting with searches that return zero results, where
the current page fails today.

- **Primary:** zero-result searches that end in a trip page view; search → trip page → booking conversion.
- **Secondary:** turns until a click on a trip, share of sessions where the user changes the search after
  a suggestion, FAQ questions answered vs "I don't have that information".
- **Guardrails:** p95 latency, cost per session, invented-fact rate. Every turn is already traced in
  Langfuse with its outcome tag, tokens, cost and latency (and logged to `logs/turns.jsonl`), so the same
  metrics as the offline eval can be read on live traffic, per release, and real conversations that went
  wrong become new scenarios.

## How I built it with AI

Built with Claude Code. `CLAUDE.md` gives the agent the architecture, the rules (business rules in
code, static prompt prefix, grounded answers) and the definition of done: tests pass, and any prompt,
tool, model or retrieval change comes with an eval run compared with the previous one. The commit history
shows that loop: each AI-stack change is committed together with the report that justifies it and the
before → after numbers.
