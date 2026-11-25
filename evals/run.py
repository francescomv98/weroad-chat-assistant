from __future__ import annotations
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from app import assistant as assistant_module
from app.assistant import Assistant, summarise_for_model
from app.config import Settings, settings
from app.data import get_catalog
from app.faq_embeddings import FaqEmbeddingIndex
from app.llm import LLMClient, OpenAIClient
from app.models import SearchState
from app.prompts import build_tools
from evals import checks

FROZEN_TODAY = date(2026, 11, 24) 
HERE = Path(__file__).resolve().parent


PROVIDERS = {
    "openai": lambda model, effort: OpenAIClient(model=model, reasoning_effort=effort or ""),
}


def build_client(spec: str) -> LLMClient:
    provider, _, rest = spec.rpartition(":")
    provider = provider or "openai"
    model, _, effort = rest.partition("@")
    if provider not in PROVIDERS:
        sys.exit(f"Provider '{provider}' is not supported yet (available: {', '.join(PROVIDERS)})")
    return PROVIDERS[provider](model, effort or None)


# RUNNING

def warm_up(label: str, client: LLMClient, faq_retrievers: list[str]) -> None:
    """One unmeasured call per model: the first request of a run also pays for opening
    the connection, which showed up as a 10-17 s "p99" that had nothing to do with the model.
    With embeddings, the FAQs are embedded here too: in production that is done once at startup,
    so it must not land in the first scenario's latency."""
    try:
        client.create(system="Reply with OK.", messages=[{"role": "user", "content": "ping"}], tools=build_tools(get_catalog()))
        if "embeddings" in faq_retrievers:
            FaqEmbeddingIndex(get_catalog().faqs).search("ping")
    except Exception as e:  # noqa: BLE001 - the real run reports the error on every turn anyway
        print(f"  warm-up failed for {label}: {e}")


def run_scenario(label: str, client: LLMClient, scenario: dict, run: int, names: list[str], catalog_text: str,
                 faq_retriever: str = "embeddings") -> list[dict]:
    bot = Assistant(llm=client, catalog=get_catalog(), today=FROZEN_TODAY, faq_retriever=faq_retriever)
    state = SearchState.model_validate(scenario.get("start", {}))
    session_id = None
    user_text = json.dumps(scenario.get("start", {}))
    records = []

    for i, turn in enumerate(scenario["turns"]):
        rec = {
            "model": label, 
            "scenario": scenario["id"], 
            "category": scenario["category"],
            "run": run, 
            "turn": i, 
            "user": turn["user"]
        }
        
        user_text += " " + turn["user"]
        before = state.model_dump(mode="json")
        history_len = len(bot.sessions[session_id].messages) if session_id else 0
        try:
            result = bot.chat(turn["user"], state, session_id)
        except Exception as e:  
            rec["error"] = f"{type(e).__name__}: {e}"
            records.append(rec)
            records += [{**rec, "turn": j, "user": t["user"], "error": None, "skipped": True}
                        for j, t in enumerate(scenario["turns"][i + 1:], start=i + 1)]
            break

        session_id, state = result.session_id, result.search.state
        messages = bot.sessions[session_id].messages
        grounded = checks.readable([m["content"] for m in messages if m["role"] == "tool"])
        rec["faq_retriever"] = faq_retriever
        rec.update(evaluate_turn(turn, before, state.model_dump(mode="json"), result, grounded, user_text, names, catalog_text))

        # FAQ retrieval is judged on what the FAQ tool returned in this turn only.
        this_turn = [m["content"] for m in messages[history_len:] if m["role"] == "tool"]
        found, admitted, faq_problems = checks.check_faq(
            turn.get("faq"), checks.faq_titles_returned(this_turn), result.reply,
            {f.id: f.title for f in bot.catalog.faqs},
        )
        rec.update(faq_found=found, faq_admitted=admitted)
        rec["problems"] += faq_problems
        rec["correct"] = rec["correct"] and not faq_problems
        records.append(rec)

    return records


def expectations(turn: dict) -> list[dict]:
    """'expect' is one correct answer; 'expect_any' lists several equally correct ones."""
    return turn.get("expect_any") or [turn.get("expect", {})]


def evaluate_turn(turn: dict, before: dict, after: dict, result, grounded: str, user_text: str,
                  names: list[str], catalog_text: str = "") -> dict:
    called = result.meta["tool_calls"]
    problems = []

    state = checks.check_state_any(before, after, expectations(turn), turn.get("allow", ()))
    if turn.get("results") == "some" and result.search.total == 0:
        state.ok = False
        state.problems.append("expected results, got none")
    if turn.get("results") == "none" and result.search.total > 0:
        state.ok = False
        state.problems.append(f"expected no results, got {result.search.total}")
    problems += state.problems

    tool_problems = checks.check_tools(called, turn.get("tools", {}))
    invented = checks.invented_facts(result.reply, grounded, user_text, names, catalog_text)
    leaked = [f"reply contains '{t}'" for t in turn.get("reply_excludes", []) if t.lower() in result.reply.lower()]
    zero_ok = None
    if result.search.total == 0:
        zero_ok = checks.offers_alternative(result.reply, summarise_for_model(result.search), names)
        if not zero_ok:
            problems.append("zero results but no concrete alternative in the reply")
    problems += tool_problems + invented + leaked

    must, must_not = turn.get("tools", {}).get("must", []), turn.get("tools", {}).get("must_not", [])
    update_label = True if "update_search" in must else False if "update_search" in must_not else None

    return {
        "reply": result.reply,
        "state": SearchState.model_validate(after).model_dump(mode="json", exclude_defaults=True),
        "total": result.search.total,
        "tool_calls": called,
        "latency_ms": result.meta["latency_ms"],
        "cost_usd": result.meta["cost_usd"],
        "usage": result.meta["usage"],
        "has_expect": any(k in turn for k in ("expect", "expect_any", "results")),
        "state_ok": state.ok,
        "tp": state.tp, "fp": state.fp, "fn": state.fn,
        "tools_ok": not tool_problems,
        "update_label": update_label,
        "update_called": "update_search" in called,
        "invented": invented,
        "zero_ok": zero_ok,
        "correct": not problems,
        "problems": problems
    }


# REPORT

def summarize(records: list[dict]) -> dict:
    done = [r for r in records if "reply" in r]
    failed = [r for r in records if r.get("error")]
    latencies = [r["latency_ms"] for r in done]
    costs = [r["cost_usd"] for r in done if r["cost_usd"] is not None]
    with_expect = [r for r in done if r["has_expect"]]
    zero = [r for r in done if r["zero_ok"] is not None]
    faq_found = [r for r in done if r.get("faq_found") is not None]
    faq_admitted = [r for r in done if r.get("faq_admitted") is not None]
    labelled = [r for r in done if r["update_label"] is not None]
    upd_tp = sum(r["update_label"] and r["update_called"] for r in labelled)
    upd_fp = sum(not r["update_label"] and r["update_called"] for r in labelled)
    upd_fn = sum(r["update_label"] and not r["update_called"] for r in labelled)
    by_category: dict[str, list[bool]] = {}
    for r in done:
        by_category.setdefault(r["category"], []).append(r["correct"])

    return {
        "requests": len(records),
        "failed": len(failed),
        "skipped": sum(1 for r in records if r.get("skipped")),
        "correct": sum(r["correct"] for r in done),
        "p50": checks.percentile(latencies, 50),
        "p95": checks.percentile(latencies, 95),
        "p99": checks.percentile(latencies, 99),
        "cost_per_turn": sum(costs) / len(costs) if costs else None,
        "total_cost": sum(costs) if costs else None,
        "state": (sum(r["state_ok"] for r in with_expect), len(with_expect)),
        "state_prf": checks.prf(sum(r["tp"] for r in done), sum(r["fp"] for r in done), sum(r["fn"] for r in done)),
        "tools": (sum(r["tools_ok"] for r in done), len(done)),
        "update_prf": checks.prf(upd_tp, upd_fp, upd_fn),
        "invented": (sum(bool(r["invented"]) for r in done), len(done)),
        "zero": (sum(r["zero_ok"] for r in zero), len(zero)),
        "faq_found": (sum(r["faq_found"] for r in faq_found), len(faq_found)),
        "faq_admitted": (sum(r["faq_admitted"] for r in faq_admitted), len(faq_admitted)),
        "by_category": {c: (sum(v), len(v)) for c, v in sorted(by_category.items())}
    }


def _ratio(pair) -> str:
    ok, total = pair
    return f"{ok}/{total} ({ok / total:.0%})" if total else "n/a"


def _pct(x) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def _ms(x) -> str:
    return "n/a" if x is None else f"{x / 1000:.2f} s"


def _usd(x) -> str:
    return "n/a" if x is None else f"${x:.5f}"


def render(summaries: dict[str, dict], records: list[dict], args) -> str:
    models = list(summaries)
    rows = [
        ("Requests (turns)", lambda s: str(s["requests"])),
        ("Correct requests", lambda s: _ratio((s["correct"], s["requests"]))),
        ("Failed requests", lambda s: _ratio((s["failed"], s["requests"]))),
        ("Latency p50", lambda s: _ms(s["p50"])),
        ("Latency p95", lambda s: _ms(s["p95"])),
        ("Latency p99", lambda s: _ms(s["p99"])),
        ("Cost / turn", lambda s: _usd(s["cost_per_turn"])),
        ("Total cost", lambda s: _usd(s["total_cost"])),
        ("Correct state (accuracy)", lambda s: _ratio(s["state"])),
        ("State fields precision", lambda s: _pct(s["state_prf"][0])),
        ("State fields recall", lambda s: _pct(s["state_prf"][1])),
        ("State fields F1", lambda s: _pct(s["state_prf"][2])),
        ("Correct tool use", lambda s: _ratio(s["tools"])),
        ("update_search precision", lambda s: _pct(s["update_prf"][0])),
        ("update_search recall", lambda s: _pct(s["update_prf"][1])),
        ("update_search F1", lambda s: _pct(s["update_prf"][2])),
        ("Turns with invented facts (lower is better)", lambda s: _ratio(s["invented"])),
        ("Zero results handled", lambda s: _ratio(s["zero"])),
        ("FAQ found (retrieval)", lambda s: _ratio(s["faq_found"])),
        ("No FAQ answer admitted", lambda s: _ratio(s["faq_admitted"]))
    ]

    lines = [
        f"# Evaluation {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Scenarios: {len({r['scenario'] for r in records})} · runs per scenario: {args.runs} · "
        f"workers: {args.workers} · frozen today: {FROZEN_TODAY} · FAQ retrievers: {', '.join(args.faq_retrievers)}",
        "",
        "| Metric | " + " | ".join(models) + " |",
        "|---|" + "---|" * len(models)
    ]
    lines += [f"| {name} | " + " | ".join(fn(summaries[m]) for m in models) + " |" for name, fn in rows]

    categories = sorted({c for s in summaries.values() for c in s["by_category"]})
    lines += ["", "## Correct requests by category", "", "| Category | " + " | ".join(models) + " |",
              "|---|" + "---|" * len(models)]
    lines += [f"| {c} | " + " | ".join(_ratio(summaries[m]["by_category"].get(c, (0, 0))) for m in models) + " |"
              for c in categories]

    lines += ["", "## What went wrong", ""]
    wrong = [r for r in records if r.get("error") or r.get("problems")]
    if not wrong:
        lines.append("Nothing: every turn passed every check.")
    for r in wrong:
        where = f"**{r['model']}** · `{r['scenario']}` turn {r['turn'] + 1} (run {r['run'] + 1})"
        why = r["error"] if r.get("error") else "; ".join(r["problems"])
        lines.append(f"- {where}: {why}")
        if r.get("reply"):
            lines.append(f"  - reply: {r['reply'][:300]!r}")
    return "\n".join(lines) + "\n"


# MAIN

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    default_model = settings.openai_model + (f"@{settings.openai_reasoning_effort}" if settings.openai_reasoning_effort else "")
    parser = argparse.ArgumentParser(description="Evaluate the assistant on scenarios.json")
    parser.add_argument("--models", nargs="+", default=[default_model], help="e.g. gpt-4.1-mini openai:gpt-5-mini@low")
    parser.add_argument("--runs", type=int, default=2, help="runs per scenario (models aren't deterministic)")
    parser.add_argument("--workers", type=int, default=4, help="parallel scenarios; use 1 for the cleanest latency numbers")
    parser.add_argument("--only", default="", help="comma-separated scenario ids or categories")
    parser.add_argument("--faq-retrievers", nargs="+", default=[settings.faq_retriever], choices=["index", "embeddings"],
                        help="FAQ retrieval to compare: the model picks from the FAQ index, or embedding search")
    args = parser.parse_args()

    scenarios = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    if args.only:
        wanted = set(args.only.split(","))
        scenarios = [s for s in scenarios if s["id"] in wanted or s["category"] in wanted]
    if not scenarios:
        sys.exit("No scenario matches --only")

    out_dir = HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)
    
    assistant_module.settings = Settings(turn_log_path=str(out_dir / "assistant_log.jsonl"))

    catalog = get_catalog()
    names = checks.trip_names([t.title for t in catalog.trips])
    # Everything that really exists: a trip-like title found nowhere in here was made up.
    catalog_text = " ".join([t.search_blob for t in catalog.trips] + catalog.travel_types
                            + catalog.destinations + [f.title for f in catalog.faqs])
    clients = {m: build_client(m) for m in args.models}
    for m, client in clients.items():
        warm_up(m, client, args.faq_retrievers)
    # One report column per (model, FAQ retriever); the retriever is named only when comparing several.
    variants = [(m if len(args.faq_retrievers) == 1 else f"{m} · {r}", m, r)
                for m in args.models for r in args.faq_retrievers]
    labels = [label for label, _, _ in variants]
    jobs = [(label, clients[m], s, run, r) for label, m, r in variants for s in scenarios for run in range(args.runs)]
    print(f"Running {len(jobs)} scenario runs ({len(scenarios)} scenarios x {args.runs} runs x {len(variants)} variants)...")

    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for recs in pool.map(lambda job: run_scenario(job[0], job[1], job[2], job[3], names, catalog_text, job[4]), jobs):
            records += recs
            r = recs[0]
            mark = "ok " if all(x.get("correct") for x in recs) else "ERR" if any(x.get("error") for x in recs) else "x  "
            print(f"  {mark} {r['model']:<24} {r['scenario']} (run {r['run'] + 1})")

    with (out_dir / "turns.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    summaries = {label: summarize([r for r in records if r["model"] == label]) for label in labels}
    report = render(summaries, records, args)
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"Saved to {out_dir}")


if __name__ == "__main__":
    main()
