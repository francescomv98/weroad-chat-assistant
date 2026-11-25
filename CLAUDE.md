# CLAUDE.md

Context for AI coding agents working on this repo. Read it before changing code.

## What this is

A chat assistant that lives on WeRoad's trip search page (hiring test, see the brief in the README of
the test). The user refines the search in natural language; the assistant turns it into structured
filters, the results list updates, and zero results is never a dead end. Sold-out departures are never shown.

Stack: Python 3, FastAPI, Pydantic v2, Anthropic Claude Haiku 5.5 (default, `LLM_PROVIDER`) or OpenAI gpt-4.1-mini,
OpenAI text-embedding-3-small for FAQ search, a single static HTML page.
Data: `samples/trips.json` (50 trips x 10 departures) and `samples/faqs.json` (50 FAQs), loaded in memory.

## Commands (Windows, from the repo root)

```powershell
venv\Scripts\python.exe run.py                     
venv\Scripts\python.exe -m pytest -q               
venv\Scripts\python.exe -m evals.run               
venv\Scripts\python.exe -m evals.run --only faq_near_miss,refine --runs 2 --workers 1
venv\Scripts\python.exe -m evals.run --models gpt-4.1-mini gpt-4o-mini
venv\Scripts\python.exe -m evals.run --faq-retrievers index embeddings
venv\Scripts\python.exe -m evals.load                     # load test with the fake LLM: free, ~1.5 min
```

`.env` needs `OPENAI_API_KEY`. Settings live in `app/config.py` (`OPENAI_MODEL`, `FAQ_RETRIEVER`, ...).

## Architecture

```
app/models.py         SearchState: the single source of truth shared by the search form and the assistant
app/search.py         exact search: every SearchState field is a hard filter; only bookable departures
app/relax.py          zero results -> cheapest changes that bring trips back (deterministic, no LLM)
app/service.py        search() = run_search + relaxations + closest trips
app/assistant.py      agent loop: tools update_search, get_trip_details, FAQ tool; sessions in memory
app/prompts.py        system prompt + tool schemas (FAQ rules/tool depend on FAQ_RETRIEVER)
app/faq_embeddings.py embedding FAQ search (default retriever); "index" = model picks from FAQ titles
app/llm.py            LLMClient protocol, OpenAI and Anthropic clients, prices and cost estimate
app/fake_llm.py       LLM_PROVIDER=fake: waits like a real call, calls nothing; only for evals/load.py
app/tracing.py        optional Langfuse traces (one per turn) and eval scores; no-op without keys, off in tests
app/main.py           FastAPI: /api/search, /api/chat, /api/chat/{id}/reset, /api/meta, /
evals/                scenarios.json, deterministic checks, run.py -> evals/results/<timestamp>/; load.py
tests/                pytest; the LLM is always a FakeLLM, embeddings a fake_embed;
                      test_invariants.py checks the business rules on random searches
```

## Rules

- **Business rules live in code, not in the prompt.** Sold-out/past departures are filtered in
  `Departure.is_bookable`, past dates are moved forward in `_move_past_dates`, relaxations are computed
  in `relax.py`. The prompt explains; the code guarantees.
- **Keep the prompt prefix static** (system prompt + tools) so OpenAI prompt caching works (~83% of
  input tokens cached). Anything that changes per turn (today, current search) goes in the `<context>`
  block of the user message, never in the system prompt or tool descriptions.
- **The model only states facts a tool returned.** No prices, dates or trips from memory; FAQ topics
  only from FAQs. If you add a tool, return small, factual JSON (see `summarise_for_model`).
- **Tool errors go back to the model** as `{"error": ...}` with `is_error`, never as exceptions to the user.
- No new dependencies unless they clearly pay off (e.g. cosine similarity is plain Python).
- Data values are fake; `today` is injectable (`Assistant(today=...)`), tests and evals freeze it.

## How changes are checked

1. `pytest` must pass. Tests never call the API: use `FakeLLM` / `call()` / `answer()` from
   `tests/test_assistant.py` and `fake_embed` for embeddings.
2. Any change to the prompt, tools, model or retrieval needs an eval run. Compare with the previous
   run in `evals/results/` and commit `report.md` + `turns.jsonl` (not `assistant_log.jsonl`) with the change.
3. Read the "What went wrong" section of the report by hand: some failures are checker false negatives.
   When a real reply is wrongly flagged, fix the check and add that reply to `tests/test_eval_checks.py`.
4. Models are not deterministic: use at least `--runs 2`, `--runs 5` before deciding between two options.
5. New scenarios go in `evals/scenarios.json` (format in its `_readme`); `test_eval_checks.py` validates ids.
   Check behaviour (state, tools, invented facts), not words: `reply_excludes` also matches refusals
   ("I can't offer it at €0").
6. A change to search or relaxation must keep `tests/test_invariants.py` green; a change to the request
   path (threads, sessions, async) is worth a `python -m evals.load` before and after.

## Conventions

- `from __future__ import annotations`, type hints, small functions, comments that explain *why*.
- Commit messages: imperative title, then `- ` bullets with what changed and, for prompt/model/retrieval
  changes, the before -> after numbers from the eval.
- Commit or push only when asked.
- Decisions and trade-offs are recorded in `DECISION.md`: update it when a choice changes.
