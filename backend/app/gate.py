"""The abstain / clarify gate.

This is the safety mechanism that makes the benchmark's **Artifact-safe** metric
a real behavior instead of an aspiration: before any municipal ticket or legal
brief is generated, the gate decides whether the pipeline is confident *enough*
to act. If it isn't, it abstains and hands back a clarifying question rather than
guessing — which is exactly what keeps **Artifact-corrupted** near zero.

There are two independent reasons to abstain:

  1. Low classification confidence — we're not sure it's infrastructure vs. legal
     (e.g. a complaint that is genuinely both, like "the council demolished my
     shop without notice").
  2. A required entity is missing or low-confidence — we can't fill the artifact
     safely (a municipal ticket with no location, a legal brief with no named
     party).

`decide()` is a pure function of (classification, extraction, config), so it is
fully unit-testable with no model, network, or database.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import ClassificationResult, Domain, EntityType, ExtractionResult


@dataclass(frozen=True)
class GateConfig:
    """Thresholds and the per-domain required-entity policy.

    Frozen so a config can be shared safely and logged verbatim alongside a
    decision (reproducibility: the report can state exactly which thresholds
    produced a given results version).
    """

    min_classification_confidence: float = 0.70
    min_entity_confidence: float = 0.60
    required_entities: dict[Domain, tuple[EntityType, ...]] = field(
        default_factory=lambda: {
            Domain.INFRASTRUCTURE: (EntityType.LOCATION, EntityType.COMPLAINT_TYPE),
            Domain.LEGAL: (EntityType.PARTY, EntityType.GRIEVANCE_TYPE),
        }
    )


@dataclass
class GateDecision:
    proceed: bool
    domain: Domain | None            # set when proceed is True
    clarifying_question: str | None  # set when proceed is False
    reasons: list[str]               # always populated, for the audit log


# The question we ask when we can't tell infrastructure from legal.
_DOMAIN_QUESTION = (
    "Just so we route this to the right place — is this mainly about a public "
    "service or infrastructure problem (water, roads, power, waste), or a legal "
    "dispute (with a landlord, an employer, the police, or similar)?"
)

# One friendly question per missing entity. We ask about a single missing item
# at a time rather than interrogating the citizen with a checklist.
_ENTITY_QUESTION: dict[EntityType, str] = {
    EntityType.LOCATION: (
        "Where exactly is this happening? A street, landmark, or area helps us "
        "send it to the right team."
    ),
    EntityType.COMPLAINT_TYPE: (
        "What is the actual problem — for example a pothole, a burst pipe, or a "
        "power outage?"
    ),
    EntityType.PARTY: (
        "Who is this complaint against — for example a landlord, an employer, or "
        "a particular office or officer?"
    ),
    EntityType.GRIEVANCE_TYPE: (
        "What kind of dispute is this — for example about tenancy, employment/"
        "labour, or police conduct?"
    ),
}


def decide(
    classification: ClassificationResult,
    extraction: ExtractionResult,
    config: GateConfig | None = None,
) -> GateDecision:
    """Decide whether to route (and where) or to abstain and ask a question."""
    config = config or GateConfig()
    reasons: list[str] = []

    # --- Reason 1: are we sure enough about infrastructure vs. legal? ---
    if classification.confidence < config.min_classification_confidence:
        reasons.append(
            f"classification confidence {classification.confidence:.2f} < threshold "
            f"{config.min_classification_confidence:.2f} (scores={classification.scores})"
        )
        return GateDecision(
            proceed=False,
            domain=None,
            clarifying_question=_DOMAIN_QUESTION,
            reasons=reasons,
        )

    # --- Reason 2: do we have the entities needed to fill this artifact safely? ---
    required = config.required_entities.get(classification.domain, ())
    missing: list[EntityType] = [
        etype
        for etype in required
        if not extraction.has_confident(etype, config.min_entity_confidence)
    ]
    if missing:
        for etype in missing:
            best = extraction.best(etype)
            if best is None:
                reasons.append(
                    f"required entity '{etype.value}' missing for "
                    f"{classification.domain.value}"
                )
            else:
                reasons.append(
                    f"required entity '{etype.value}' confidence {best.confidence:.2f} < "
                    f"threshold {config.min_entity_confidence:.2f}"
                )
        return GateDecision(
            proceed=False,
            domain=None,
            clarifying_question=_ENTITY_QUESTION[missing[0]],
            reasons=reasons,
        )

    # --- Confident and complete: safe to route. ---
    reasons.append(
        f"classification confidence {classification.confidence:.2f} >= "
        f"{config.min_classification_confidence:.2f}; all required entities present "
        f"for {classification.domain.value}"
    )
    return GateDecision(
        proceed=True,
        domain=classification.domain,
        clarifying_question=None,
        reasons=reasons,
    )
