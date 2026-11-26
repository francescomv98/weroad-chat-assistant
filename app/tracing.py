"""Optional tracing of the assistant to Langfuse (https://langfuse.com).

One trace per chat turn, grouped in a session per conversation, with one `generation` per LLM call
(model, tokens, cost) and one `tool` observation per tool call (arguments, result). The assistant is
instrumented here, not inside each provider's client, so OpenAI and Anthropic turns look the same.

Off unless configured: in the app it turns on when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set
(LANGFUSE_BASE_URL picks the region, EU by default); the eval turns it on only with --langfuse; tests
keep it off. When it's off every helper is a no-op, and a tracing failure never breaks a chat turn."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from . import config  # noqa: F401  (imported for its load_dotenv(): the LANGFUSE_* keys can come from .env)

log = logging.getLogger(__name__)

_client: Any = None
_configured = False
# The startup warm-up and the first chat turn can configure at the same time: one sets it up, the other
# waits, and `_configured` turns true only once the client exists (otherwise a turn could see "configured"
# with no client yet and go untraced).
_lock = threading.RLock()
# Extra tags and metadata for the traces started inside `context()` (the eval: run, scenario, model...).
_extra: ContextVar[tuple[tuple[str, ...], dict[str, str]]] = ContextVar("tracing_extra", default=((), {}))
# Tags of the turn being traced, so tags added at the end of the turn keep the ones set at its start.
_turn_tags: ContextVar[tuple[str, ...]] = ContextVar("tracing_turn_tags", default=())


def release() -> str | None:
    """The code version on every trace, so Langfuse can compare cost, latency and failures before and after
    a change: LANGFUSE_RELEASE if set, otherwise the git commit (+"-dirty" with uncommitted changes)."""
    if os.getenv("LANGFUSE_RELEASE"):
        return os.environ["LANGFUSE_RELEASE"]
    repo = Path(__file__).resolve().parents[1]
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True,
                             timeout=3, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo,
                               capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"{sha}-dirty" if dirty else sha or None


class _NoOp:
    """Stands in for a Langfuse observation when tracing is off."""

    def update(self, **_: Any) -> None:
        pass


def configure(enabled: bool | None = None, environment: str | None = None, client: Any = None) -> None:
    """enabled=None: on when the Langfuse keys are set. `client` injects a fake in tests."""
    global _configured
    with _lock:
        try:
            _setup(enabled, environment, client)
        finally:
            _configured = True


def _setup(enabled: bool | None, environment: str | None, client: Any) -> None:
    global _client
    if client is not None:
        _client = client
        return
    if enabled is None:
        enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
    _client = None
    if not enabled:
        return
    try:
        from langfuse import Langfuse, is_langfuse_span
    except ImportError:
        log.error("Langfuse keys are set but the langfuse package isn't installed in this Python (%s): "
                  "use the project's venv or pip install -r requirements.txt. Tracing is off.", sys.executable)
        return
    try:
        _client = Langfuse(
            environment=environment or os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or "development",
            release=release(),
            # Only the observations created here. The Anthropic SDK emits its own OpenTelemetry span for every
            # call ("anthropic.messages.create"), which Langfuse would pick up as a second, empty generation
            # inside each of ours (23 extra in eval 20261125-161556).
            should_export_span=is_langfuse_span,
        )
    except Exception:
        log.exception("Langfuse could not start: tracing is off")


def _get() -> Any:
    if not _configured:
        with _lock:
            if not _configured:
                configure()
    return _client


def enabled() -> bool:
    return _get() is not None


def flush() -> None:
    """Send what is still buffered (the eval calls it before exiting)."""
    if _get() is not None:
        _client.flush()


@contextmanager
def _observe(name: str, as_type: str, **fields: Any) -> Generator[Any]:
    client = _get()
    if client is None:
        yield _NoOp()
        return
    with client.start_as_current_observation(name=name, as_type=as_type, **fields) as obs:
        try:
            yield obs
        except Exception as e:
            obs.update(level="ERROR", status_message=f"{type(e).__name__}: {e}")
            raise


@contextmanager
def context(tags: list[str], metadata: dict[str, str]) -> Generator[None]:
    """Traces started inside get these tags and metadata too, without the code in between knowing."""
    extra_tags, extra_meta = _extra.get()
    token = _extra.set((extra_tags + tuple(tags), {**extra_meta, **metadata}))
    try:
        yield
    finally:
        _extra.reset(token)


@contextmanager
def turn(session_id: str, message: str, metadata: dict[str, str], tags: list[str] | None = None) -> Generator[Any]:
    """The root of a trace: one chat turn. `metadata` (short strings) is copied onto every observation."""
    client = _get()
    if client is None:
        yield _NoOp()
        return
    from langfuse import propagate_attributes

    extra_tags, extra_meta = _extra.get()
    all_tags = (*extra_tags, *(tags or []))
    token = _turn_tags.set(all_tags)
    try:
        with _observe("chat-turn", "agent", input=message) as root:
            with propagate_attributes(session_id=session_id, trace_name="chat-turn", metadata={**extra_meta, **metadata},
                                      tags=list(all_tags) or None):
                yield root
    finally:
        _turn_tags.reset(token)


def add_tags(tags: list[str]) -> None:
    """Tags known only when the turn ends (its outcome). Call inside `turn`, after the turn's work."""
    if _get() is None or not tags:
        return
    from langfuse import propagate_attributes

    merged = tuple(dict.fromkeys((*_turn_tags.get(), *tags)))
    _turn_tags.set(merged)
    with propagate_attributes(tags=list(merged)):  # sets them on the turn's root observation
        pass


def current_trace_id() -> str | None:
    """The trace being recorded right now (inside `turn`), or None when tracing is off."""
    client = _get()
    return client.get_current_trace_id() if client is not None else None


def score(trace_id: str | None, name: str, value: bool | float, comment: str | None = None) -> None:
    """Attach a verdict to a trace: booleans as Langfuse BOOLEAN scores (1/0), numbers as NUMERIC."""
    client = _get()
    if client is None or not trace_id:
        return
    is_bool = isinstance(value, bool)
    try:
        client.create_score(trace_id=trace_id, name=name, value=float(value),
                            data_type="BOOLEAN" if is_bool else "NUMERIC", comment=comment)
    except Exception:  # noqa: BLE001 - a lost score must not stop the eval
        log.exception("could not send score %s", name)


def generation(name: str, model: str, input: Any, model_parameters: dict | None = None):
    return _observe(name, "generation", model=model, input=input, model_parameters=model_parameters)


def tool(name: str, input: Any):
    return _observe(name, "tool", input=input)


# What the observations show

def history(messages: list[dict]) -> list[dict]:
    """The conversation as the model saw it, readable: provider-specific raw blocks are left out."""
    out = []
    for m in messages:
        item: dict[str, Any] = {"role": m["role"], "content": m.get("content")}
        if m.get("tool_calls"):
            item["tool_calls"] = [{"name": tc.name, "arguments": tc.arguments} for tc in m["tool_calls"]]
        if m["role"] == "tool":
            item["content"] = parse_json(m["content"])
        out.append(item)
    return out


def usage_details(usage: dict[str, int]) -> dict[str, int]:
    names = {"input_tokens": "input", "cached_input_tokens": "input_cached",
             "cache_write_input_tokens": "input_cache_write", "output_tokens": "output"}
    return {names[k]: v for k, v in usage.items() if k in names and v}


def parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text
