"""A fake LLM provider for load tests (LLM_PROVIDER=fake, see evals/load.py).

It answers like the real providers do in a typical turn, a search then a short reply, and waits like they
do, but calls no API: a load test then measures this server (threads, sessions, search, relaxation)
without spending tokens or hitting the provider's rate limits.
"""
from __future__ import annotations

import itertools
import json
import time
import uuid

from .config import settings
from .llm import LLMResponse, ToolCall

# Searches the fake LLM cycles through: with and without results, so a load test also runs the relaxation.
FAKE_SEARCHES = (
    {"continents": ["Asia"]},
    {"continents": ["Europe"], "max_price": 1500},
    {"destinations": ["Japan"], "max_price": 900},  # zero results -> relaxation
    {"must_have": ["cooking"], "min_days": 7}
)


class FakeClient:
    """Stands in for the provider in load tests: every call waits like a real one and costs nothing,
    so a load test measures this server (threads, sessions, search, relaxation), not the provider.
    First call of a turn: an update_search tool call; after the tool result: a short reply."""

    provider = "fake"
    model = "fake"

    def __init__(self, latency_s: float | None = None) -> None:
        self.latency_s = settings.fake_llm_latency_s if latency_s is None else latency_s
        self._turns = itertools.count()

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        time.sleep(self.latency_s)
        if messages and messages[-1]["role"] == "tool":
            return LLMResponse(text="Here are some trips for you.", tool_calls=[], stop="end")
        args = FAKE_SEARCHES[next(self._turns) % len(FAKE_SEARCHES)]
        call = ToolCall(id=f"fake-{uuid.uuid4().hex[:8]}", name="update_search", arguments=dict(args),
                        raw_arguments=json.dumps(args))
        return LLMResponse(text="", tool_calls=[call], stop="tool_use")
