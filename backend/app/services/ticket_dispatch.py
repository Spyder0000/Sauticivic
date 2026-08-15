"""Mock municipal ticket dispatch — generates a structured ticket artifact.

Takes the routed infrastructure outcome (entities, transcript) and produces a
ticket dict that represents what a real ServiceNow/Jira-style API would return.
The tracking ID is deterministic from the transcript hash so tests are stable.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..schemas import EntityType, ExtractionResult


def generate_ticket(
    transcript: str,
    extraction: ExtractionResult,
    *,
    timestamp: datetime | None = None,
) -> dict:
    """Generate a mock municipal infrastructure ticket.

    Returns a dict (the artifact) that mirrors what a real dispatch system would
    produce: tracking ID, location, complaint type, status, description, and
    timestamps. This is the thing that gets stored in the `artifact` field of
    IntakeOutcome and audited.
    """
    ts = timestamp or datetime.now(timezone.utc)

    # Deterministic tracking ID from transcript content — stable for tests.
    digest = hashlib.sha256(transcript.encode()).hexdigest()[:8].upper()
    tracking_id = f"TKT-{ts.strftime('%Y%m%d')}-{digest}"

    # Pull entities; fall back to "unspecified" so the ticket is always complete.
    location_entity = extraction.best(EntityType.LOCATION)
    complaint_entity = extraction.best(EntityType.COMPLAINT_TYPE)

    return {
        "artifact_type": "municipal_ticket",
        "tracking_id": tracking_id,
        "status": "dispatched",
        "location": location_entity.value if location_entity else "unspecified",
        "complaint_type": complaint_entity.value if complaint_entity else "unspecified",
        "description": transcript,
        "created_at": ts.isoformat(),
        "priority": "normal",
    }
