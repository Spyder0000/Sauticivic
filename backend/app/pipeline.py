"""Intake orchestration: transcript -> extract -> classify -> gate -> outcome.

Kept pure and synchronous so the whole decision path is testable without
FastAPI, a database, or a model SDK. The router (routers/intake.py) is a thin
async wrapper over `run_intake`; the voice path will differ only in that it
first calls the Sahara ASR service to produce the transcript, then feeds the
exact same pipeline.
"""
from __future__ import annotations

from .agents.classifier_agent import ClassifierAgent
from .agents.extraction_agent import ExtractionAgent
from .gate import GateConfig, decide
from .schemas import IntakeOutcome, OutcomeStatus


def run_intake(
    transcript: str,
    *,
    extractor: ExtractionAgent | None = None,
    classifier: ClassifierAgent | None = None,
    config: GateConfig | None = None,
) -> IntakeOutcome:
    """Run one complaint transcript through the full decision path.

    Returns an IntakeOutcome that is either ROUTED (with a domain) or
    NEEDS_CLARIFICATION (with a question). Crucially, an artifact is only ever
    generated downstream when status is ROUTED — the gate is the single choke
    point, so a wrong artifact can't be produced by skipping it.
    """
    extractor = extractor or ExtractionAgent()
    classifier = classifier or ClassifierAgent()

    extraction = extractor.run(transcript)
    classification = classifier.run(transcript)
    decision = decide(classification, extraction, config)

    # Chain the classifier's reasoning and the gate's reasoning for the audit log.
    reasons = list(classification.reasons) + list(decision.reasons)

    if decision.proceed:
        return IntakeOutcome(
            status=OutcomeStatus.ROUTED,
            transcript=transcript,
            classification=classification,
            extraction=extraction,
            domain=decision.domain,
            reasons=reasons,
        )
    return IntakeOutcome(
        status=OutcomeStatus.NEEDS_CLARIFICATION,
        transcript=transcript,
        classification=classification,
        extraction=extraction,
        clarifying_question=decision.clarifying_question,
        reasons=reasons,
    )
