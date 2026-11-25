from __future__ import annotations
from typing import Annotated
from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from . import config, service
from .assistant import Assistant
from .data import get_catalog
from .llm import LLMProviderError
from .models import SearchResponse, SearchState

app = FastAPI(title="WeRoad search assistant")
_assistant: Assistant | None = None
STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def get_assistant() -> Assistant:
    global _assistant
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


@app.get("/api/meta")
def meta() -> dict:
    catalog = get_catalog()
    return {
        "today": config.today().isoformat(),
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
        raise HTTPException(e.status, e.message)
    return ChatResponse(session_id=turn.session_id, reply=turn.reply, search=turn.search, meta=turn.meta)


@app.post("/api/chat/{session_id}/reset")
def reset(session_id: Annotated[str, PathParam(pattern=SESSION_ID_PATTERN)]) -> dict:
    get_assistant().reset(session_id)
    return {"ok": True}