# WeRoad trip search assistant

A chat assistant that lives next to WeRoad's trip search. You describe the trip you want in your own
words ("somewhere warm in Asia in March, under €1500, not too physical"); the assistant turns it into
search filters, the results list on the page updates, and when nothing matches it explains what is
blocking and proposes the closest options instead of a dead end. It also answers practical questions
(visas, flights, group size...) from WeRoad's FAQs.

- **Natural language → structured filters**: the assistant edits the same search the form uses, so what it
  says and what the page shows always agree.
- **Zero results is never a dead end**: the cheapest changes that bring trips back (dates ±7 days, budget
  +15%, ...), each with its real result count, computed in code.
- **Business rules in code, not in the prompt**: sold-out and past departures are never shown.
- **Grounded answers**: prices, dates and trips only from the search; practical answers only from the FAQs.
- **Measured**: 84 evaluation scenarios, 130 tests, a load test, optional tracing with Langfuse.

Stack: Python 3.13, FastAPI, Claude Haiku 5.5 (or OpenAI gpt-4.1-mini), OpenAI embeddings for FAQ
search, a single static HTML page. The data (`samples/`: 50 trips × 10 departures, 50 FAQs) is fake and
loaded in memory.

### The brief's requirements, and where they are met

| Requirement | How | Where |
|---|---|---|
| Start from the user's current search | Every chat message carries the page's search; the assistant edits that same object | `app/models.py` (`SearchState`), `app/assistant.py` |
| Refine in natural language over several turns | Tools that update the search, conversation kept per session | `app/prompts.py`, `app/sessions.py` |
| Sold-out departures never shown | Filtered in code on every search, whatever the model says; also past departures | `Departure.is_bookable` in `app/data.py`, `tests/test_invariants.py` |
| Zero results is not a dead end | Cheapest relaxations with their real result counts, plus the closest trips | `app/relax.py`, `app/service.py` |

Choices, trade-offs, what was left out and what I'd ship first: [DECISION.md](DECISION.md). The AI
workflow is in [CLAUDE.md](CLAUDE.md) (the agent's instructions), the commit history and the eval runs
committed in `evals/results/`.

## Run it

### Requirements

- Python 3.13
- An **Anthropic API key** for the chat (or an `ant auth login` profile, see below)
- An **OpenAI API key** for the FAQ search (embeddings). Without one, set `FAQ_RETRIEVER=index`: the
  model then picks FAQs from their titles, and only Claude is needed.

### Windows (PowerShell)

```powershell
git clone https://github.com/francescomv98/weroad-chat-assistant.git
cd weroad-chat-assistant
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env        # then open .env and fill in ANTHROPIC_API_KEY and OPENAI_API_KEY
venv\Scripts\python.exe run.py
```

### macOS / Linux

```bash
git clone https://github.com/francescomv98/weroad-chat-assistant.git
cd weroad-chat-assistant
python3 -m venv venv
venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env          # then fill in ANTHROPIC_API_KEY and OPENAI_API_KEY
venv/bin/python run.py
```

`run.py` starts the server on http://127.0.0.1:8000 and **opens the browser when the assistant is
ready**: at startup it loads the SDKs in the background, ~15-30 s on Windows, a few seconds on Linux.
`--no-browser` keeps it from opening. `requirements.txt` alone is enough to run the app;
`requirements-dev.txt` adds the tools for tests and lint.

**Port 8000 already in use** (another project, a container)? The page you get is then the other
program's. Pick another port: `$env:PORT = "8080"; venv\Scripts\python.exe run.py` (PowerShell) or
`PORT=8080 venv/bin/python run.py`.

### Docker

```powershell
docker build -t weroad-chat .
docker run -p 8000:8000 --env-file .env weroad-chat
```

Then open http://localhost:8000 (a container can't open your browser). Keys are passed when the
container starts and never stored in the image.

Every release is also published as an image: `ghcr.io/francescomv98/weroad-chat` (`latest`, or a
version such as `1.0.0`).

### Things to try

- Type `party trip asia` in the search bar: 0 results (the bar needs every word to match). Then ask the
  assistant *"a party trip in Asia"*: it turns it into filters and the trips appear.
- *"something in Asia for culture lovers"*, then *"under 1500 euros"*, then *"only trips with a cooking
  class"*: each turn refines the same search.
- *"Japan for under 900 euros"*: nothing matches, the assistant shows what's blocking and the closest
  options, and asks which trade-off you prefer.
- *"I only have 19–24 October"*: dates in the past move to the next year; no departures then, so it
  proposes the nearest dates.
- *"are flights included?"*, or with Peru selected *"what money do they use there?"*: answers from the FAQs.
- *"can I bring my dog on the trip?"*: no FAQ covers it, and the assistant says so instead of inventing
  a policy.

## Configuration

All settings are environment variables, read from `.env` (see `.env.example` for the full list and
`app/config.py` for the defaults).

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | | Claude, for the chat |
| `OPENAI_API_KEY` | | FAQ embeddings; also the chat with `LLM_PROVIDER=openai` |
| `LLM_PROVIDER` | `anthropic` | `anthropic`, `openai`, or `fake` (load tests: calls nothing) |
| `ANTHROPIC_MODEL` / `ANTHROPIC_EFFORT` | `claude-haiku-5-5` / `low` | Claude model and thinking effort |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI chat model |
| `FAQ_RETRIEVER` | `embeddings` | `embeddings` (search the FAQ text) or `index` (the model picks from titles) |
| `FIXED_TODAY` | real date | The date the app treats as today, e.g. `2026-11-24`. The sample departures run from 2026-10-12 to 2027-09-29: set it to demo the data after it has aged |
| `PORT` | `8000` | Port used by `run.py` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | | Optional: one trace per chat turn in Langfuse |

## How it works

```
 page (search form + results + chat)
   │  POST /api/chat {message, current search}
   ▼
 Assistant (app/assistant.py) ── LLM: Claude Haiku 5.5 ── tools:
   │                                  update_search     → search + relaxations
   │                                  get_trip_details  → one trip
   │                                  search_faqs       → FAQ embeddings
   ▼
 reply + new search → the page re-renders the results
```

1. Every message carries the page's current search, so the assistant always starts from what the user
   sees.
2. The model changes the search through `update_search`; the code applies it as exact filters and only
   returns bookable departures.
3. If nothing matches, `app/relax.py` computes the cheapest changes that bring trips back, each with its
   result count; the assistant asks which trade-off the user prefers.
4. Practical questions go to the FAQ search: the question is embedded and compared with the FAQ
   vectors, which are computed once by an ingestion step (`python -m app.faq_ingest`) and stored in
   `samples/faq_vectors.json`.
5. Conversations are kept in memory per session (1 hour idle, at most 5,000). The search itself lives
   in the page and its URL, so a reload or an expired session never loses it.

API: `POST /api/search` (search without the assistant), `POST /api/chat`, `POST /api/chat/{id}/reset`,
`GET /api/ready` (startup warm-up done?), `GET /api/meta`. Interactive docs at
http://127.0.0.1:8000/docs.

### Project layout

```
app/
  main.py            FastAPI app and endpoints; startup warm-up
  models.py          SearchState: the search shared by the form and the assistant
  search.py          exact search: every field is a hard filter, only bookable departures
  relax.py           zero results → the cheapest changes that bring trips back (no LLM)
  service.py         search + relaxations + closest trips
  assistant.py       the agent loop and its tools
  prompts.py         system prompt and tool definitions
  faq_embeddings.py  FAQ search by embeddings
  faq_ingest.py      ingestion: FAQ embeddings into samples/faq_vectors.json
  sessions.py        conversation memory (in memory, bounded)
  llm.py             Claude and OpenAI clients behind one interface, costs
  tracing.py         optional Langfuse tracing
  static/index.html  the page
samples/             trips, FAQs, FAQ vectors
tests/               pytest, no API calls (fake LLM, fake embeddings)
evals/               scenarios, checks, eval runner, load test, committed results
```

## Tests and quality

```powershell
venv\Scripts\python.exe -m pytest -q                        # 130 tests, no API keys, ~1 min
venv\Scripts\ruff.exe check .                               # lint
venv\Scripts\python.exe -m evals.run                        # LLM evaluation: needs keys, 2 runs, ~$0.10-0.25
venv\Scripts\python.exe -m evals.run --runs 10 --workers 1  # more runs, cleanest latency numbers
venv\Scripts\python.exe -m evals.load                       # load test with a fake LLM: free, ~1.5 min
```

- **Tests** never call an API. `tests/test_invariants.py` checks the business rules on 400 random
  searches over the real data: every result bookable and within every filter, zero results never a
  dead end.
- **The eval** (`evals/`) runs 84 scenarios on the real data with a frozen date: refinements, dates,
  multi-turn, zero results, vague requests, FAQs in several languages, adversarial messages. Checks are
  deterministic (search state, tools called, invented prices or trips), no LLM judge. Each run writes
  `evals/results/<timestamp>/report.md`, with a "What went wrong" section to read by hand.
- **The load test** runs the real server with a fake LLM: about 18 turns/s per process.

## Development workflow

Git Flow: `master` is what's released, `develop` the next release; work happens on `feature/<name>`
branches with a pull request into `develop`. Releases (`release/x.y.z`) and urgent fixes
(`hotfix/x.y.z`) end in a `vX.Y.Z` tag on `master`.

GitHub Actions:
- **CI**, on pull requests and on pushes to `develop`: tests, Docker build with a smoke test (fake LLM),
  ruff, pip-audit (known vulnerabilities in the dependencies) and semgrep (security analysis). No API
  keys, no cost.
- **CD**, on `master` and `v*` tags: CI, then the image is published to GitHub's container registry.

The LLM eval isn't in CI (it needs keys and costs money): any change to the prompt, tools, model or
retrieval comes with an eval run committed in `evals/results/`.

## More

- [DECISION.md](DECISION.md): what was built, what was left out and why, with the numbers from the evals
  (model choice, FAQ retrieval, prompt caching, capacity, observability).
- [CLAUDE.md](CLAUDE.md): rules and commands for AI coding agents working on this repo.
