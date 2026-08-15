"""Shared, dependency-free data types for the SautiCivic intake pipeline.

These are plain stdlib dataclasses/enums on purpose: the core logic
(extraction, classification, and the abstain gate) can be imported and
unit-tested without FastAPI, a database, or any model SDK installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Domain(str, Enum):
    """Where a complaint gets routed."""

    INFRASTRUCTURE = "infrastructure"            # -> municipal ticket
    LEGAL = "legal"                              # -> legal aid intake brief
    NEEDS_CLARIFICATION = "needs_clarification"  # -> abstain, ask the citizen


class EntityType(str, Enum):
    """The entities a downstream artifact needs in order to be filled safely."""

    LOCATION = "location"              # landmark / street / area for a municipal ticket
    COMPLAINT_TYPE = "complaint_type"  # pothole / burst pipe / power outage ...
    PARTY = "party"                    # who a legal grievance is against
    GRIEVANCE_TYPE = "grievance_type"  # tenancy / labour / police-conduct ...


@dataclass(frozen=True)
class Entity:
    type: EntityType
    value: str
    confidence: float  # 0..1


@dataclass
class ExtractionResult:
    """Entities pulled from a transcript, each with its own confidence."""

    entities: list[Entity] = field(default_factory=list)

    def best(self, etype: EntityType) -> Entity | None:
        """Highest-confidence entity of a given type, or None if absent."""
        matches = [e for e in self.entities if e.type == etype]
        return max(matches, key=lambda e: e.confidence, default=None)

    def has_confident(self, etype: EntityType, min_confidence: float) -> bool:
        """True iff an entity of this type exists at or above min_confidence."""
        best = self.best(etype)
        return best is not None and best.confidence >= min_confidence


@dataclass
class ClassificationResult:
    """Infra-vs-legal routing decision. The classifier only ever emits
    INFRASTRUCTURE or LEGAL; NEEDS_CLARIFICATION is the *gate's* call, not the
    classifier's."""

    domain: Domain
    confidence: float                                # 0..1
    reasons: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)  # per-domain raw signal (for the audit log)


class OutcomeStatus(str, Enum):
    ROUTED = "routed"                            # confident enough -> artifact will be generated
    NEEDS_CLARIFICATION = "needs_clarification"  # gate abstained -> ask instead of guessing


@dataclass
class IntakeOutcome:
    """The final result of one intake.

    Either we ROUTED (and `domain` + `artifact` say where and what was generated),
    or we abstained and set `clarifying_question`. `reasons` is always populated
    so every decision is explainable in the audit log.
    """

    status: OutcomeStatus
    transcript: str
    classification: ClassificationResult | None = None
    extraction: ExtractionResult | None = None
    domain: Domain | None = None            # set when status == ROUTED
    artifact: dict | None = None            # the generated ticket or brief; set when status == ROUTED
    clarifying_question: str | None = None  # set when status == NEEDS_CLARIFICATION
    reasons: list[str] = field(default_factory=list)

