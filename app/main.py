"""The FastAPI app: the page and the API (/api/search, /api/chat, /api/chat/{id}/reset, /api/ready,
/api/meta), plus the background warm-up at startup."""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi import Path as PathParam
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, service, tracing
from .assistant import Assistant
from .data import get_catalog
from .llm import LLMProviderError
from .models import SearchResponse, SearchState

# uvicorn's logger: its INFO lines are shown in the console, the app's own loggers only from WARNING.
log = logging.getLogger("uvicorn.error")
_assistant: Assistant | None = None
_assistant_lock = threading.Lock()
# Set when the warm-up has finished (or isn't running): /api/ready and /api/meta report it, so run.py opens
# the browser and the page enables Send only when the first reply will be fast.
assistant_ready = threading.Event()


class _HideReadinessPolls(logging.Filter):
    """run.py and the page poll /api/ready about once a second during the warm-up: keep those lines
    out of the console so the log still shows the requests that matter."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/ready" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HideReadinessPolls())
STATIC_DIR = Path(__file__).resolve().parent / "static"


def warm_up() -> None:
    """Load now what the first chat would otherwise wait for (~15 s, see `warmup` in config.py).
    Each step on its own: one that fails (a missing key) is logged and the chat reports it as usual."""
    started = time.perf_counter()
    steps = (
        ("assistant", get_assistant),
        ("LLM client", lambda: getattr(get_assistant().llm, "_get_client", lambda: None)()),
        ("tracing", tracing.enabled),
        ("FAQ embeddings", lambda: get_assistant().faq_index and get_assistant().faq_index.vectors()),
    )
    try:
        for name, step in steps:
            try:
                step()
            except Exception as e:  # noqa: BLE001 - a warm-up failure must never stop the server
                log.warning("warm-up: %s failed: %s", name, e)
        log.info("warm-up done in %.1f s", time.perf_counter() - started)
    finally:
        assistant_ready.set()  # even after a failure: the chat then reports the error itself


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    # In a thread, so the page and the search answer at once; a chat sent during the warm-up waits only
    # for what isn't loaded yet.
    if config.settings.warmup:
        assistant_ready.clear()
        threading.Thread(target=warm_up, name="warm-up", daemon=True).start()
    else:
        assistant_ready.set()
    yield


app = FastAPI(title="WeRoad search assistant", lifespan=lifespan)
# The page's own files (the WeRoad icon for the tab and the header) at /static/...
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def get_assistant() -> Assistant:
    global _assistant
    if _assistant is None:
        with _assistant_lock:  # the warm-up and the first request may both get here: build it once
            if _assistant is None:
                _assistant = Assistant()
    return _assistant


# The session id comes from the client and ends up in logs and traces: accept only what the server hands
# out (uuid4 hex) or something like it, so a forged id can't add lines to the log or grow without limit.
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    state: SearchState = Field(default_factory=SearchState)
    session_id: str | None = Field(default=None, pattern=SESSION_ID_PATTERN)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    search: SearchResponse
    meta: dict


@app.get("/api/ready")
def ready() -> dict:
    return {"assistant_ready": assistant_ready.is_set()}


@app.get("/api/meta")
def meta() -> dict:
    catalog = get_catalog()
    return {
        "today": config.today().isoformat(),
        "assistant_ready": assistant_ready.is_set(),
        "continents": catalog.continents,
        "destinations": catalog.destinations,
        "travel_types": catalog.travel_types
    }


@app.post("/api/search", response_model=SearchResponse)
def search(state: SearchState) -> SearchResponse:
    return service.search(state)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        turn = get_assistant().chat(req.message, req.state, req.session_id)
    except LLMProviderError as e:
        raise HTTPException(e.status, e.message) from e
    return ChatResponse(session_id=turn.session_id, reply=turn.reply, search=turn.search, meta=turn.meta)


@app.post("/api/chat/{session_id}/reset")
def reset(session_id: Annotated[str, PathParam(pattern=SESSION_ID_PATTERN)]) -> dict:
    get_assistant().reset(session_id)
    return {"ok": True}
