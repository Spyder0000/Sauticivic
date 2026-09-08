"""Intake orchestration: transcript -> extract -> classify -> gate -> artifact -> outcome.

Kept pure and synchronous so the whole decision path is testable without
FastAPI, a database, or a model SDK. The router (routers/intake.py) is a thin
async wrapper over `run_intake`; the voice path will differ only in that it
first calls the Sahara ASR service to produce the transcript, then feeds the
exact same pipeline.
"""
from __future__ import annotations

from pathlib import Path

from .agents.classifier_agent import ClassifierAgent
from .agents.extraction_agent import ExtractionAgent
from .audit import log_outcome
from .gate import GateConfig, decide
from .schemas import Domain, IntakeOutcome, OutcomeStatus
from .services.legal_brief_generator import generate_brief
from .services.ticket_dispatch import generate_ticket


def run_intake(
    transcript: str,
    *,
    extractor: ExtractionAgent | None = None,
    classifier: ClassifierAgent | None = None,
    config: GateConfig | None = None,
    audit_log_path: Path | str | None = None,
    session_id: str | None = None,
) -> IntakeOutcome:
    """Run one complaint transcript through the full decision path.

    Returns an IntakeOutcome that is either ROUTED (with a domain and a
    populated artifact) or NEEDS_CLARIFICATION (with a question and no
    artifact). The gate is the single choke point — a wrong artifact can't
    be produced by skipping it.
    """
    extractor = extractor or ExtractionAgent()
    classifier = classifier or ClassifierAgent()

    extraction = extractor.run(transcript)
    classification = classifier.run(transcript)
    decision = decide(classification, extraction, config, transcript=transcript)

    # Chain the classifier's reasoning and the gate's reasoning for the audit log.
    reasons = list(classification.reasons) + list(decision.reasons)

    if decision.proceed:
        # --- Generate the domain-specific artifact ---
        artifact: dict | None = None
        if decision.domain == Domain.INFRASTRUCTURE:
            artifact = generate_ticket(transcript, extraction)
        elif decision.domain == Domain.LEGAL:
            artifact = generate_brief(transcript, extraction)

        outcome = IntakeOutcome(
            status=OutcomeStatus.ROUTED,
            transcript=transcript,
            classification=classification,
            extraction=extraction,
            domain=decision.domain,
            artifact=artifact,
            reasons=reasons,
        )
    else:
        outcome = IntakeOutcome(
            status=OutcomeStatus.NEEDS_CLARIFICATION,
            transcript=transcript,
            classification=classification,
            extraction=extraction,
            clarifying_question=decision.clarifying_question,
            reasons=reasons,
        )

    # --- Audit: log every outcome, routed or abstained ---
    if audit_log_path is not None:
        log_outcome(outcome, log_path=audit_log_path, session_id=session_id)

    return outcome
