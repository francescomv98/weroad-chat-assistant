"""Settings read from environment variables (and .env): provider, models, FAQ retrieval, sessions,
timeouts. `today()` is the date the whole app uses (FIXED_TODAY or the real date)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_reasoning_effort: str = os.getenv("OPENAI_REASONING_EFFORT", "")
    # Optional label OpenAI uses to route requests sharing the system prompt and tools to the same cache.
    # Off by default: an A/B test in the same time window (80 calls each, alternating) showed no difference
    # (37 vs 34 calls missed the cache entirely). Empty = not sent.
    openai_prompt_cache_key: str = os.getenv("OPENAI_PROMPT_CACHE_KEY", "")
    # Which LLM runs the assistant: "anthropic" (default, needs ANTHROPIC_API_KEY), "openai", or "fake" (load tests).
    # Claude Haiku 5.5 at low effort: in eval 20261125-144136 Haiku 5.5 matched gpt-4.1-mini on quality
    # (172/172 vs 170/172) at less than half the cost per turn; low effort to cut thinking latency.
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    # LLM_PROVIDER=fake (load tests only): no API call, each LLM call just waits this long. 1 s per call,
    # two calls per turn, is close to a real Haiku @low turn (p50 2.6 s).
    fake_llm_latency_s: float = float(os.getenv("FAKE_LLM_LATENCY_S", "1.0"))
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
    # low | medium | high | xhigh | max; empty = the model's default (medium on Haiku 5.5).
    anthropic_effort: str = os.getenv("ANTHROPIC_EFFORT", "low")
    # Seconds per LLM call before the SDK gives up; the SDKs retry twice on timeouts, 429 and 5xx. 30 s is
    # ~7x the p99 of a Haiku @low turn (4.4 s) and caps a stuck call at ~1.5 min instead of 3-6 min.
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "30"))
    # In-memory sessions: dropped after this many seconds without a message, and at most this many kept
    # (least recently used go first). A 10-turn chat is ~17 KB (~20-40 KB with Claude's thinking blocks),
    # so 5,000 sessions stay under ~200 MB.
    session_ttl_s: float = float(os.getenv("SESSION_TTL_S", "3600"))
    session_max: int = int(os.getenv("SESSION_MAX", "5000"))
    # Load the slow parts in the background when the server starts, not on the first chat: importing the
    # anthropic SDK alone takes ~11 s on Windows, Langfuse 2.5-5 s, openai ~4 s, the FAQ embeddings ~2.4 s,
    # so the first reply took ~15 s. 0 = off (the load test, which must call nothing).
    warmup: bool = os.getenv("WARMUP", "1") != "0"
    max_tool_rounds: int = int(os.getenv("ASSISTANT_MAX_TOOL_ROUNDS", "6"))
    turn_log_path: str = os.getenv("TURN_LOG_PATH", "logs/turns.jsonl")
    # How the model finds FAQs: "embeddings" (it writes a query, FAQs ranked by similarity with
    # text-embedding-3-small) or "index" (it picks from the list of FAQ titles). Embeddings are the
    # default: same recall, but they search the FAQ text, not only titles (see evals/results/20261125-095057).
    faq_retriever: str = os.getenv("FAQ_RETRIEVER", "embeddings")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    faq_min_similarity: float = float(os.getenv("FAQ_MIN_SIMILARITY", "0.3"))
    # The date the app treats as "today" (YYYY-MM-DD), e.g. to demo the sample data as it was on a given
    # day: departures before it are not bookable, relative dates resolve from it. Empty = the real date.
    fixed_today: str = os.getenv("FIXED_TODAY", "")

    def __post_init__(self) -> None:
        if self.fixed_today:
            try:
                date.fromisoformat(self.fixed_today)
            except ValueError:
                raise ValueError(f"FIXED_TODAY must be a date like 2026-11-24, got {self.fixed_today!r}") from None


settings = Settings()


def today() -> date:
    """Today for the whole app: FIXED_TODAY if set, otherwise the real date.
    Reads `settings` at call time, so tests can replace it."""
    return date.fromisoformat(settings.fixed_today) if settings.fixed_today else date.today()
