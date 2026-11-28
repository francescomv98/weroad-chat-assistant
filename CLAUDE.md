# CLAUDE.md

Context for AI coding agents working on this repo. Read it before changing code.

## What this is

A chat assistant that lives on WeRoad's trip search page (hiring test, see the brief in the README of
the test). The user refines the search in natural language; the assistant turns it into structured
filters, the results list updates, and zero results is never a dead end. Sold-out departures are never shown.

Stack: Python 3, FastAPI, Pydantic v2, Anthropic Claude Haiku 5.5 (default, `LLM_PROVIDER`) or OpenAI gpt-4.1-mini,
OpenAI text-embedding-3-small for FAQ search, a single static HTML page.
Data: `samples/trips.json` (50 trips x 10 departures) and `samples/faqs.json` (50 FAQs), loaded in memory;
`samples/faq_vectors.json` holds the FAQ embeddings, written by `python -m app.faq_ingest`.

## Commands (Windows, from the repo root)

```powershell
venv\Scripts\python.exe run.py                     
venv\Scripts\python.exe -m pytest -q               
venv\Scripts\python.exe -m evals.run               
venv\Scripts\python.exe -m evals.run --only faq_near_miss,refine --runs 2 --workers 1
venv\Scripts\python.exe -m evals.run --models gpt-4.1-mini gpt-4o-mini
venv\Scripts\python.exe -m evals.run --faq-retrievers index embeddings
venv\Scripts\python.exe -m evals.load                     # load test with the fake LLM: free, ~1.5 min
venv\Scripts\python.exe -m app.faq_ingest                 # after editing faqs.json: re-embed, commit faq_vectors.json
venv\Scripts\ruff.exe check .                             # lint (rules in pyproject.toml); --fix for the safe fixes
venv\Scripts\pip-audit.exe -r requirements-dev.txt        # known CVEs in the pinned packages
docker run --rm -v "${PWD}:/src" -w /src semgrep/semgrep:1.160.0 semgrep scan --error --metrics off --config p/python --config p/fastapi --config p/secrets --config p/dockerfile --exclude venv --exclude evals/results --exclude logs
```

Docker (Docker Desktop running; keys passed at run time, never in the image):

```powershell
docker build -t weroad-chat .
docker run -p 8000:8000 --env-file .env -e ANTHROPIC_API_KEY weroad-chat
```

Then open http://localhost:8000 (the browser doesn't open by itself: the container can't start programs on the host).

- **Credentials** are read at `docker run`, never stored in the image: `.env` is passed by `--env-file`, and
  `-e ANTHROPIC_API_KEY` copies the key from the shell if it is set there instead of in `.env`.
- **With an `ant auth login` profile** instead of a key, pass a short-lived token (PowerShell only: cmd doesn't
  run `$( )`), and start the container again with a new one when it expires:
  `docker run -p 8000:8000 --env-file .env -e "ANTHROPIC_AUTH_TOKEN=$(ant auth print-credentials --access-token)" weroad-chat`.
  Mounting the profile folder doesn't work: files shared from Windows are writable by everyone, and the SDK
  refuses them as credentials.
- **Port 8000 busy** (another project, or `run.py`)? Map another one: `-p 8080:8000`, then http://localhost:8080.
- `.dockerignore` lists what goes in the image (app, samples, requirements); everything else, `.env` included,
  stays out. One process only: sessions are in its memory.

Credentials: Claude (the chat, default provider) from `ANTHROPIC_API_KEY` or, without it, an `ant auth login`
profile, which the SDK finds by itself; `OPENAI_API_KEY` in `.env` (FAQ embeddings, and the chat with
`LLM_PROVIDER=openai`); `LANGFUSE_*` keys are optional. Settings live in `app/config.py`
(`LLM_PROVIDER`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `FAQ_RETRIEVER`, ...).

## Architecture

```
app/models.py         SearchState: the single source of truth shared by the search form and the assistant
app/search.py         exact search: every SearchState field is a hard filter; only bookable departures
app/relax.py          zero results -> cheapest changes that bring trips back (deterministic, no LLM)
app/service.py        search() = run_search + relaxations + closest trips
app/assistant.py      agent loop: tools update_search, get_trip_details, FAQ tool
app/sessions.py       SessionStore (get/save/delete); in memory with idle expiry and a cap; Redis would plug in here
app/prompts.py        system prompt + tool schemas (FAQ rules/tool depend on FAQ_RETRIEVER)
app/faq_embeddings.py embedding FAQ search (default retriever); "index" = model picks from FAQ titles
app/faq_ingest.py     ingestion: embeds the FAQs once into samples/faq_vectors.json (no OpenAI call at startup)
app/llm.py            LLMClient protocol, OpenAI and Anthropic clients, prices and cost estimate
app/fake_llm.py       LLM_PROVIDER=fake: waits like a real call, calls nothing; only for evals/load.py
app/tracing.py        optional Langfuse traces (one per turn) and eval scores; no-op without keys, off in tests
app/main.py           FastAPI: /api/search, /api/chat, /api/chat/{id}/reset, /api/meta, /, /static; startup warm-up
evals/                scenarios.json, deterministic checks, run.py -> evals/results/<timestamp>/; load.py
tests/                pytest; the LLM is always a FakeLLM, embeddings a fake_embed;
                      test_invariants.py checks the business rules on random searches
```

## Rules

- **Business rules live in code, not in the prompt.** Sold-out/past departures are filtered in
  `Departure.is_bookable`, past dates are moved forward in `_move_past_dates`, relaxations are computed
  in `relax.py`. The prompt explains; the code guarantees.
- **Keep the prompt prefix static** (system prompt + tools) so prompt caching works on both providers
  (Claude: `cache_control` in `llm.py`; OpenAI: automatic, ~83% of input tokens cached). Anything that changes per turn (today, current search) goes in the `<context>`
  block of the user message, never in the system prompt or tool descriptions. User text never carries
  `<context>` tags (they are stripped in `_turn`), so the only block the model sees is ours.
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

## Branches (Git Flow) and CI/CD

- `master`: what is released; every commit there is published as a Docker image. `develop`: the next release.
- New work: `feature/<name>` from `develop`, pull request back into `develop`.
- A release: `release/<x.y.z>` from `develop` (only fixes there), merged into `master` with tag `v<x.y.z>`
  and back into `develop`. An urgent fix: `hotfix/<x.y.z>` from `master`, merged into both, tagged.
- `.github/workflows/ci.yml`: on pushes to `develop` and on pull requests into `develop`/`master` (feature,
  release and hotfix branches are tested through their pull request): pytest, Docker build, and a smoke test of the image with the fake LLM
  (page, search, chat); ruff and pip-audit; semgrep. No API keys, no cost. Run ruff before pushing
  (commands above). A semgrep false positive gets `# nosemgrep: <rule-id>` with the reason, not a looser config. It doesn't run the eval: that needs keys and costs money, so
  it stays a manual step (rule 2 above).
- `.github/workflows/cd.yml`: on pushes to `master` and `v*` tags: CI first, then the image to
  `ghcr.io/<owner>/weroad-chat` (`latest`, `sha-<commit>`, and `<x.y.z>`/`<x.y>` for tags). On pull requests
  into `master` it builds the image without pushing it: unmerged code is never published.
- Check workflow edits with actionlint before pushing:
  `docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:latest` (PowerShell).

## Conventions

- `from __future__ import annotations`, type hints, small functions, comments that explain *why*.
- Commit messages: imperative title, then `- ` bullets with what changed and, for prompt/model/retrieval
  changes, the before -> after numbers from the eval.
- Commit or push only when asked.
- Decisions and trade-offs are recorded in `DECISION.md`: update it when a choice changes.
