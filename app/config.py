from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_reasoning_effort: str = os.getenv("OPENAI_REASONING_EFFORT", "")
    max_tool_rounds: int = int(os.getenv("ASSISTANT_MAX_TOOL_ROUNDS", "6"))
    turn_log_path: str = os.getenv("TURN_LOG_PATH", "logs/turns.jsonl")


settings = Settings()
