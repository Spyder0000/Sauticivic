"""Dependency-free JSONL audit logger.

Appends one JSON line per intake outcome to a local file. This is the
lightweight, always-available audit trail — no database required. Every
outcome (routed with artifact, or abstained with clarifying question) is
recorded with full reasoning.

The DB-backed audit log (when Postgres is wired) will be a second,
queryable copy — this file-based log is the fallback that never fails
and doubles as the benchmark's input/output record.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .schemas import IntakeOutcome

# Default log path — overridable via environment or function argument.
_DEFAULT_LOG_PATH = Path("audit_log.jsonl")


def log_outcome(
    outcome: IntakeOutcome,
    *,
    log_path: Path | str | None = None,
    session_id: str | None = None,
) -> dict:
    """Append a single outcome to the JSONL audit log.

    Returns the logged record dict (useful for tests and the benchmark harness).
    """
    path = Path(log_path) if log_path else _DEFAULT_LOG_PATH

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "status": outcome.status.value,
        "transcript": outcome.transcript,
        "domain": outcome.domain.value if outcome.domain else None,
        "artifact": outcome.artifact,
        "clarifying_question": outcome.clarifying_question,
        "reasons": outcome.reasons,
        "classification": {
            "domain": outcome.classification.domain.value,
            "confidence": outcome.classification.confidence,
            "scores": outcome.classification.scores,
        } if outcome.classification else None,
        "entities": [
            {"type": e.type.value, "value": e.value, "confidence": e.confidence}
            for e in (outcome.extraction.entities if outcome.extraction else [])
        ],
    }

    # Ensure parent directory exists.
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record
