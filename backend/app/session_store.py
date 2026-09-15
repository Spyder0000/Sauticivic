"""In-memory session store for clarification chains.

Tracks per-session state between the initial intake and each clarification
round. Single-process only — adequate for the dev/demo server and for the
challenge submission.

When Postgres is fully wired (Week 3+), this can be replaced with a DB-backed
store without changing the router — the router just calls get_session() and
save_session() and doesn't care where the data lives.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SessionState:
    session_id: str
    original_transcript: str
    clarification_rounds: list[str] = field(default_factory=list)  # each clarification answer
    llm_call_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_store: dict[str, SessionState] = {}
_lock = threading.Lock()


def create_session(transcript: str) -> str:
    """Create a new session for an intake transcript. Returns the session_id."""
    session_id = str(uuid.uuid4())
    with _lock:
        _store[session_id] = SessionState(
            session_id=session_id,
            original_transcript=transcript,
        )
    return session_id


def get_session(session_id: str) -> SessionState | None:
    with _lock:
        return _store.get(session_id)


def add_clarification(session_id: str, clarification: str) -> SessionState | None:
    """Append a clarification answer to the session. Returns updated state or None."""
    with _lock:
        state = _store.get(session_id)
        if state is None:
            return None
        state.clarification_rounds.append(clarification)
        return state


def record_llm_call(session_id: str) -> SessionState | None:
    """Reserve one of the two optional LLM calls permitted for a case."""
    with _lock:
        state = _store.get(session_id)
        if state is None:
            return None
        state.llm_call_count += 1
        return state


def build_combined_transcript(state: SessionState) -> str:
    """Combine the original transcript with all clarification answers.

    Feeds into run_intake() for re-classification. The combined context
    gives the classifier and extractor more signal than the original alone.
    """
    parts = [state.original_transcript]
    for i, clarification in enumerate(state.clarification_rounds, start=1):
        parts.append(f"[Clarification {i}]: {clarification}")
    return " ".join(parts)
