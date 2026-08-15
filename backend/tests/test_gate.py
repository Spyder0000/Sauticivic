"""Tests for the abstain/clarify gate and the intake pipeline.

Run from the repo root with:  PYTHONPATH=backend python3 -m pytest backend/tests -q

The gate tests build ClassificationResult/ExtractionResult by hand so they test
the *decision logic* in isolation (independent of the mock model's NLP quality).
The pipeline tests then exercise the mock backends end to end.
"""
from app.gate import GateConfig, decide
from app.pipeline import run_intake
from app.schemas import (
    ClassificationResult,
    Domain,
    Entity,
    EntityType,
    ExtractionResult,
    OutcomeStatus,
)


def _infra_entities() -> ExtractionResult:
    return ExtractionResult(
        [
            Entity(EntityType.LOCATION, "Allen Avenue", 0.80),
            Entity(EntityType.COMPLAINT_TYPE, "burst pipe", 0.90),
        ]
    )


def _legal_entities() -> ExtractionResult:
    return ExtractionResult(
        [
            Entity(EntityType.PARTY, "landlord", 0.85),
            Entity(EntityType.GRIEVANCE_TYPE, "eviction", 0.85),
        ]
    )


# --------------------------- gate unit tests ---------------------------

def test_confident_infra_with_entities_proceeds():
    d = decide(ClassificationResult(Domain.INFRASTRUCTURE, 0.90), _infra_entities())
    assert d.proceed
    assert d.domain is Domain.INFRASTRUCTURE
    assert d.clarifying_question is None


def test_confident_legal_with_entities_proceeds():
    d = decide(ClassificationResult(Domain.LEGAL, 0.90), _legal_entities())
    assert d.proceed
    assert d.domain is Domain.LEGAL


def test_low_classification_confidence_abstains():
    d = decide(ClassificationResult(Domain.INFRASTRUCTURE, 0.50), _infra_entities())
    assert not d.proceed
    assert d.domain is None
    assert d.clarifying_question  # asks the infra-vs-legal question


def test_missing_required_location_abstains():
    ex = ExtractionResult([Entity(EntityType.COMPLAINT_TYPE, "pothole", 0.90)])  # no location
    d = decide(ClassificationResult(Domain.INFRASTRUCTURE, 0.95), ex)
    assert not d.proceed
    assert "location" in " ".join(d.reasons)


def test_low_confidence_entity_is_treated_as_missing():
    ex = ExtractionResult(
        [
            Entity(EntityType.PARTY, "landlord", 0.40),  # below the 0.60 entity threshold
            Entity(EntityType.GRIEVANCE_TYPE, "rent", 0.90),
        ]
    )
    d = decide(ClassificationResult(Domain.LEGAL, 0.95), ex)
    assert not d.proceed


def test_custom_thresholds_are_respected():
    cfg = GateConfig(min_classification_confidence=0.60)
    d = decide(ClassificationResult(Domain.INFRASTRUCTURE, 0.65), _infra_entities(), cfg)
    assert d.proceed  # would have abstained under the default 0.70


def test_every_decision_has_reasons():
    d = decide(ClassificationResult(Domain.LEGAL, 0.90), _legal_entities())
    assert d.reasons  # explainability: never an empty rationale


# ----------------------- pipeline integration tests -----------------------

def test_pipeline_routes_clear_infrastructure():
    out = run_intake("There is a big pothole on the road for Allen Avenue, e don spoil our tyre.")
    assert out.status is OutcomeStatus.ROUTED
    assert out.domain is Domain.INFRASTRUCTURE


def test_pipeline_routes_clear_legal():
    out = run_intake("My landlord wan evict me and refuse to return my rent deposit.")
    assert out.status is OutcomeStatus.ROUTED
    assert out.domain is Domain.LEGAL


def test_pipeline_abstains_on_ambiguous_complaint():
    # "landlord ... burst pipe" carries both legal and infrastructure signal;
    # the margin is thin, so the gate should ask rather than guess.
    out = run_intake("My landlord refused to fix the burst pipe in the flat.")
    assert out.status is OutcomeStatus.NEEDS_CLARIFICATION
    assert out.clarifying_question


def test_pipeline_abstains_on_no_signal():
    out = run_intake("Abeg I get one small problem, make una help me.")
    assert out.status is OutcomeStatus.NEEDS_CLARIFICATION
