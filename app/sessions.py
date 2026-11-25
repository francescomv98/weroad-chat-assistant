"""Where conversations live between turns.

The interface (get / save / delete) is the one a Redis store would have: the assistant loads a session,
runs the turn and saves it only if the turn succeeded. In production a RedisSessionStore with the same
three methods (history as JSON, an expiry on each key) would let several processes share sessions.
"""
from __future__ import annotations
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Protocol


@dataclass
class Session:
    id: str
    messages: list[dict] = field(default_factory=list)


class SessionStore(Protocol):
    def get(self, session_id: str) -> Session | None: ...

    def save(self, session: Session) -> None: ...

    def delete(self, session_id: str) -> None: ...


class MemorySessionStore:
    """Sessions in this process's memory, bounded in time and number.

    Without a bound every conversation stayed in memory until the process restarted. A session idle for
    more than `ttl_s` is gone (the page sends the current search with every message, so the user keeps
    their results; only the chat history is forgotten). Above `max_sessions` the least recently used
    goes first. A lock because FastAPI runs chat requests in parallel threads.
    """

    def __init__(self, ttl_s: float, max_sessions: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_s = ttl_s
        self.max_sessions = max_sessions
        self._clock = clock
        # Ordered by last save, oldest first: expired and least recently used sessions are at the front.
        self._sessions: OrderedDict[str, tuple[float, Session]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            self._drop_expired()
            entry = self._sessions.get(session_id)
            return entry[1] if entry else None

    def save(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.id] = (self._clock(), session)
            self._sessions.move_to_end(session.id)
            self._drop_expired()
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        with self._lock:
            self._drop_expired()
            return len(self._sessions)

    def _drop_expired(self) -> None:
        """From the front only: stops at the first session still fresh, so a call costs O(expired)."""
        cutoff = self._clock() - self.ttl_s
        while self._sessions:
            saved_at, _ = next(iter(self._sessions.values()))
            if saved_at > cutoff:
                break
            self._sessions.popitem(last=False)
