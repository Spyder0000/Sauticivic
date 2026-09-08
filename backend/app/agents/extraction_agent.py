"""Extraction agent — entity extraction (location, party names, complaint type).

Pluggable by design: `ExtractionAgent` runs whatever `ExtractionBackend` it is
given. The default `MockExtractionBackend` is a dependency-free, deterministic
heuristic so the pipeline and the abstain gate can be built and tested *before*
the real LLM/Sahara-backed extractor exists. Swap the backend later; the gate
and pipeline never change.
"""
from __future__ import annotations

import re
from typing import Protocol

from ..schemas import Entity, EntityType, ExtractionResult

# --- Mock keyword vocabularies (placeholder heuristics, not the real extractor) ---
_COMPLAINT_KEYWORDS = {
    "pothole", "road", "pipe", "water", "burst", "leak", "power", "electricity",
    "light", "streetlight", "outage", "nepa", "waste", "garbage", "refuse",
    "drainage", "gutter", "sewage", "flood", "blocked", "blockage",
    "bridge", "crack", "borehole",
}
_PARTY_KEYWORDS = {
    "landlord", "employer", "boss", "oga", "company", "police", "officer", "agent",
    "neighbour", "neighbor", "tenant", "contractor", "manager",
    "security", "partner", "husband",
}
_GRIEVANCE_KEYWORDS = {
    "rent", "evict", "eviction", "tenancy", "salary", "wage", "wages", "overtime",
    "entitlement", "sack", "sacked", "fired", "labour", "labor", "arrest", "arrested", "detain",
    "detained", "beat", "beaten", "harass", "harassment", "assault", "contract", "deposit",
    "fraud", "neglect", "dispute",
}

# A capitalized phrase after a locational preposition, e.g. "for Ojota",
# "at Allen Avenue". Deliberately conservative — the mock would rather miss a
# location (and let the gate ask) than invent one.
_LOCATION_RE = re.compile(
    r"\b(?:at|for|near|along|in|on|around)\s+([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){0,3})"
)
_PLACE_WORDS = {
    "junction", "market", "estate", "street", "road", "avenue", "close", "area",
    "bridge", "roundabout", "expressway",
}


def _matches(text_lower: str, vocab: set[str]) -> list[str]:
    """Whole-word (case-insensitive) hits from a vocabulary, de-duplicated."""
    return sorted({w for w in vocab if re.search(rf"\b{re.escape(w)}\b", text_lower)})


class ExtractionBackend(Protocol):
    """Anything that can turn a transcript into a list of entities."""

    def extract(self, transcript: str) -> list[Entity]: ...


class MockExtractionBackend:
    """Deterministic keyword/regex extractor. Placeholder for the real model.

    Confidences are heuristic (more corroborating tokens -> higher). They exist
    so the abstain gate has something meaningful to threshold on; they are not
    calibrated probabilities.
    """

    def extract(self, transcript: str) -> list[Entity]:
        low = transcript.lower()
        entities: list[Entity] = []

        for etype, vocab in (
            (EntityType.COMPLAINT_TYPE, _COMPLAINT_KEYWORDS),
            (EntityType.PARTY, _PARTY_KEYWORDS),
            (EntityType.GRIEVANCE_TYPE, _GRIEVANCE_KEYWORDS),
        ):
            hits = _matches(low, vocab)
            if hits:
                confidence = min(0.95, 0.70 + 0.10 * (len(hits) - 1))
                entities.append(Entity(type=etype, value=", ".join(hits), confidence=confidence))

        # Location: prefer an explicit "<prep> <Capitalized>" span; fall back to a
        # bare place-type word with lower confidence.
        loc = _LOCATION_RE.search(transcript)
        if loc:
            entities.append(Entity(EntityType.LOCATION, loc.group(1).strip(), 0.80))
        else:
            place_hits = _matches(low, _PLACE_WORDS)
            if place_hits:
                entities.append(Entity(EntityType.LOCATION, ", ".join(place_hits), 0.60))

        return entities


class ExtractionAgent:
    def __init__(self, backend: ExtractionBackend | None = None) -> None:
        self.backend: ExtractionBackend = backend or MockExtractionBackend()

    def run(self, transcript: str) -> ExtractionResult:
        return ExtractionResult(entities=list(self.backend.extract(transcript)))
