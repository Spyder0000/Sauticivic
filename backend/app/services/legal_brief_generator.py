"""Legal Aid Intake Brief generator — produces a structured brief artifact.

Takes the routed legal outcome (entities, transcript) and produces a brief dict
that represents the structured document a paralegal would normally spend 45+
minutes drafting manually. PDF rendering is a later concern — at this stage the
artifact is a structured dict/JSON.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..schemas import EntityType, ExtractionResult


def generate_brief(
    transcript: str,
    extraction: ExtractionResult,
    *,
    timestamp: datetime | None = None,
) -> dict:
    """Generate a structured Legal Aid Intake Brief.

    Returns a dict (the artifact) containing: brief ID, respondent party,
    grievance type, statement of facts (the transcript), and intake metadata.
    This is stored in IntakeOutcome.artifact and audited.
    """
    ts = timestamp or datetime.now(timezone.utc)
    local_ts = ts.astimezone()

    # Deterministic brief ID from transcript content — stable for tests.
    digest = hashlib.sha256(transcript.encode()).hexdigest()[:8].upper()
    brief_id = f"BRIEF-{ts.strftime('%Y%m%d')}-{digest}"

    # Pull entities; fall back to "unspecified" so the brief is always complete.
    party_entity = extraction.best(EntityType.PARTY)
    grievance_entity = extraction.best(EntityType.GRIEVANCE_TYPE)

    return {
        "artifact_type": "legal_brief",
        "case_id": f"CASE-{digest}",
        "brief_id": brief_id,
        "status": "draft_ready_for_confirmation",
        "is_draft": True,
        "dispatch_notice": "Draft only — SautiCivic has not contacted a legal organization.",
        "respondent": party_entity.value if party_entity else "unspecified",
        "grievance_type": grievance_entity.value if grievance_entity else "unspecified",
        "statement_of_facts": transcript,
        "complainant": "anonymous",
        "created_at": ts.isoformat(),
        "local_created_at": local_ts.isoformat(),
        "priority": "normal",
        "department": "Legal-aid intake",
    }
