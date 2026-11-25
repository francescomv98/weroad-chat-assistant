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
