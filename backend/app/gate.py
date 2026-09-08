"""The abstain / clarify gate.

This is the safety mechanism that makes the benchmark's **Artifact-safe** metric
a real behavior instead of an aspiration: before any municipal ticket or legal
brief is generated, the gate decides whether the pipeline is confident *enough*
to act. If it isn't, it abstains and hands back a clarifying question rather than
guessing — which is exactly what keeps **Artifact-corrupted** near zero.

There are three independent reasons to abstain:

  1. Danger signal override — the transcript contains physical violence, criminal
     conduct, unlawful confinement, extortion, or fire. Routed silently as a
     routine ticket in these cases causes direct harm; forced abstention is the
     only safe response.
  2. Low classification confidence — we're not sure it's infrastructure vs. legal
     (e.g. a complaint that is genuinely both, like "the council demolished my
     shop without notice").
  3. A required entity is missing or low-confidence — we can't fill the artifact
     safely (a municipal ticket with no location, a legal brief with no named
     party).

`decide()` is a pure function of (classification, extraction, config, transcript),
so it is fully unit-testable with no model, network, or database.
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


# ---------------------------------------------------------------------------
# Danger signal detection — two tiers
# ---------------------------------------------------------------------------
#
# Tier 1 — EMERGENCY signals: block ALL routing (infrastructure AND legal).
#   These indicate an active life-safety emergency (fire, toxic exposure, active
#   physical confinement) where even a legal brief is the wrong first response.
#   The citizen needs emergency services triage, not a ticket or a brief.
#
# Tier 2 — CRIMINAL / EXTORTION signals: block INFRASTRUCTURE routing only.
#   Violence, extortion, unlawful confinement etc. should route to LEGAL (legal
#   aid is exactly who handles these). Blocking infrastructure is correct because
#   a municipal ticket would silently drop the criminal element; legal routing is safe.

_EMERGENCY_PATTERNS: list[tuple[str, str]] = [
    # Active fire / explosion
    ("fire start", "active fire emergency detected"),
    ("fire.*generator", "fire near fuel source detected"),
    ("toxic smoke", "hazardous chemical / fire emergency detected"),
    ("acid", "hazardous chemical assault detected"),
]

_CRIMINAL_PATTERNS: list[tuple[str, str]] = [
    # Physical violence / assault
    ("beat", "physical assault detected"),
    ("break her", "physical assault detected"),
    ("armed thugs", "armed criminal conduct detected"),
    ("armed", "armed threat detected"),
    # Unlawful confinement / imprisonment
    ("lock the exit", "unlawful confinement detected"),
    ("lock.*gate.*chain", "unlawful confinement detected"),
    ("lock.*inside", "unlawful confinement detected"),
    ("lock.*outside", "unlawful eviction/confinement detected"),
    ("chained inside", "unlawful confinement detected"),
    ("padlock", "forced entry / unlawful confinement detected"),
    ("seize my.*id", "unlawful document confiscation detected"),
    ("seize my.*certificate", "unlawful document confiscation detected"),
    ("seize my.*national", "unlawful document confiscation detected"),
    # Extortion / illegal levies
    ("illegal levy", "state-linked extortion detected"),
    ("bribe", "officer extortion detected"),
    ("extortion", "extortion detected"),
    ("ten thousand naira", "vigilante extortion detected"),
    ("fifty thousand naira", "extortion detected"),
    # Demolition as punishment / armed land grab
    ("demolish", "punitive demolition / land-grab detected"),
    ("bulldozer", "forced demolition detected"),
    # Retaliatory / coercive utility disconnection
    ("disconnect.*wire", "retaliatory utility disconnection detected"),
    ("disconnect.*transformer", "retaliatory utility disconnection detected"),
]

_DANGER_QUESTION = (
    "Before we route this, we need to understand the full situation. "
    "It sounds like there may be a safety risk or criminal element involved — "
    "can you tell us more about what happened so we can connect you with the "
    "right support, which may include emergency services or legal protection?"
)

_EMERGENCY_QUESTION = (
    "This sounds like it may involve an immediate safety emergency. "
    "Please contact emergency services (112 or your local emergency number) right away "
    "if anyone is in immediate danger. Once you're safe, we can help you file a formal "
    "complaint — can you tell us more about what happened?"
)


def _detect_emergency(transcript: str) -> tuple[bool, str]:
    """Check for Tier 1 life-safety emergencies that block ALL routing."""
    import re
    lower = transcript.lower()
    for pattern, reason in _EMERGENCY_PATTERNS:
        if re.search(pattern, lower):
            return True, reason
    return False, ""


def _detect_criminal(transcript: str) -> tuple[bool, str]:
    """Check for Tier 2 criminal signals that block INFRASTRUCTURE routing only."""
    import re
    lower = transcript.lower()
    for pattern, reason in _CRIMINAL_PATTERNS:
        if re.search(pattern, lower):
            return True, reason
    return False, ""


# ---------------------------------------------------------------------------
# Gate questions
# ---------------------------------------------------------------------------

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
    transcript: str = "",
) -> GateDecision:
    """Decide whether to route (and where) or to abstain and ask a question."""
    config = config or GateConfig()
    reasons: list[str] = []

    # --- Reason 0: danger signal overrides (highest priority, two tiers) ---
    if transcript:
        # Tier 1: active life-safety emergency — blocks ALL routing (infra AND legal).
        # A fire or chemical emergency needs emergency services, not any kind of brief.
        is_emergency, emergency_reason = _detect_emergency(transcript)
        if is_emergency:
            reasons.append(
                f"emergency override: {emergency_reason} — forced abstention "
                f"(active life-safety emergency requires emergency services triage, "
                f"not a routed ticket or brief)"
            )
            return GateDecision(
                proceed=False,
                domain=None,
                clarifying_question=_EMERGENCY_QUESTION,
                reasons=reasons,
            )

        # Tier 2: criminal / extortion signal — blocks INFRASTRUCTURE routing only.
        # Violence, extortion, and unlawful confinement should route to LEGAL (correct).
        # They must NOT generate an infrastructure ticket (silently drops the crime).
        if classification.domain == Domain.INFRASTRUCTURE:
            is_criminal, criminal_reason = _detect_criminal(transcript)
            if is_criminal:
                reasons.append(
                    f"criminal signal override: {criminal_reason} — forced abstention "
                    f"(infrastructure ticket must not be issued for a complaint involving "
                    f"violence, extortion, or unlawful confinement)"
                )
                return GateDecision(
                    proceed=False,
                    domain=None,
                    clarifying_question=_DANGER_QUESTION,
                    reasons=reasons,
                )

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
