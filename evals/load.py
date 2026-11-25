"""Load test of the chat API with the fake LLM: measures this server, not the provider, and costs nothing.

    venv\\Scripts\\python.exe -m evals.load                       # 1, 10, 20, 40, 80 users
    venv\\Scripts\\python.exe -m evals.load --users 1 40 120 --turns 5

It starts its own server with LLM_PROVIDER=fake (each LLM call just waits FAKE_LLM_LATENCY_S), tracing off
and the turn log in a temp folder. Each simulated user sends --turns messages in one session, one after
the other with no pause, so N users = N chats in flight at any time. For every level it prints throughput
and latency: as long as the server keeps up, latency stays near the fake LLM time; when it can't, turns
queue and latency grows with the number of users.

The provider's own limits are not measured here: compare its published rate limits with the tokens per
turn from the eval (see DECISION.md).
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from evals.checks import percentile

MESSAGES = ["somewhere in Asia", "under 1500 euros", "Japan for under 900", "with a cooking class"]


def post(url: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except OSError:  # connection refused/reset, timeout
        return 0, {}


def one_user(base: str, turns: int) -> list[tuple[float, int]]:
    """One chat: `turns` messages in the same session. Returns (seconds, HTTP status) per turn."""
    out, session = [], None
    for i in range(turns):
        started = time.perf_counter()
        status, body = post(f"{base}/api/chat", {"message": MESSAGES[i % len(MESSAGES)], "session_id": session})
        out.append((time.perf_counter() - started, status))
        session = body.get("session_id", session)
    return out


def run_level(base: str, users: int, turns: int) -> dict:
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=users) as pool:
        results = [r for user in pool.map(lambda _: one_user(base, turns), range(users)) for r in user]
    elapsed = time.perf_counter() - started
    ok = [s for s, status in results if status == 200]
    return {
        "users": users,
        "turns": len(results),
        "errors": len(results) - len(ok),
        "turns_per_s": len(ok) / elapsed,
        "p50": percentile(ok, 50),
        "p95": percentile(ok, 95),
        "max": max(ok, default=None),
    }


def start_server(port: int, latency: float, log_dir: str) -> subprocess.Popen:
    env = {
        **os.environ,
        "LLM_PROVIDER": "fake",
        "FAKE_LLM_LATENCY_S": str(latency),
        "TURN_LOG_PATH": os.path.join(log_dir, "turns.jsonl"),
        # Empty, not missing: load_dotenv doesn't override variables that exist, so .env keys stay unused.
        "LANGFUSE_PUBLIC_KEY": "",
        "LANGFUSE_SECRET_KEY": "",
    }
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        env=env,
    )
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/meta", timeout=1)
            return server
        except OSError:
            time.sleep(0.5)
    server.kill()
    raise SystemExit("the server did not start")


def fmt(seconds: float | None) -> str:
    return "-" if seconds is None else f"{seconds:.2f} s"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--users", type=int, nargs="+", default=[1, 10, 20, 40, 80])
    parser.add_argument("--turns", type=int, default=3, help="messages per simulated user")
    parser.add_argument("--latency", type=float, default=1.0, help="seconds per fake LLM call (2 calls per turn)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as log_dir:
        server = start_server(args.port, args.latency, log_dir)
        try:
            base = f"http://127.0.0.1:{args.port}"
            print(f"Fake LLM: {args.latency} s per call, so a turn takes at least {2 * args.latency:.1f} s\n")
            print("| Users | Turns | Errors | Turns/s | p50 | p95 | Max |")
            print("|---|---|---|---|---|---|---|")
            for users in args.users:
                r = run_level(base, users, args.turns)
                print(f"| {r['users']} | {r['turns']} | {r['errors']} | {r['turns_per_s']:.1f} | "
                      f"{fmt(r['p50'])} | {fmt(r['p95'])} | {fmt(r['max'])} |", flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
