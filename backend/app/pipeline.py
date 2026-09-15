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
from .services.deepseek_layer import request_artifact_draft, request_clarification


def normalize_transcript(transcript: str) -> str:
    """Conservative display normalization; never rewrites the citizen's words."""
    return " ".join(transcript.split())


def run_intake(
    transcript: str,
    *,
    extractor: ExtractionAgent | None = None,
    classifier: ClassifierAgent | None = None,
    config: GateConfig | None = None,
    audit_log_path: Path | str | None = None,
    session_id: str | None = None,
    allow_llm: bool = False,
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

    normalized = normalize_transcript(transcript)

    if decision.proceed:
        # --- Generate the domain-specific artifact ---
        artifact: dict | None = None
        if decision.domain == Domain.INFRASTRUCTURE:
            artifact = generate_ticket(transcript, extraction)
        elif decision.domain == Domain.LEGAL:
            artifact = generate_brief(transcript, extraction)

        if allow_llm and artifact is not None:
            entity_fields = {entity.type.value: entity.value for entity in extraction.entities}
            draft = request_artifact_draft(
                domain=decision.domain.value,
                transcript=normalized,
                fields=entity_fields,
            )
            artifact["draft_title"] = draft.title
            artifact["draft_summary"] = draft.summary
            artifact["routing_explanation"] = draft.routing_explanation
            artifact["drafting_layer"] = "deepseek_or_deterministic_fallback"

        outcome = IntakeOutcome(
            status=OutcomeStatus.ROUTED,
            transcript=transcript,
            classification=classification,
            extraction=extraction,
            domain=decision.domain,
            artifact=artifact,
            reasons=reasons,
            normalized_transcript=normalized,
            safety_gate_result="passed",
        )
    else:
        is_emergency = any(reason.startswith("emergency override:") for reason in decision.reasons)
        # DeepSeek is permitted only for genuine domain ambiguity. Missing entity
        # questions remain deterministic and the gate decision is never changed.
        if allow_llm and classification.confidence < (config or GateConfig()).min_classification_confidence and not is_emergency:
            suggestion = request_clarification(transcript=normalized, missing_field="domain")
            question = suggestion.question
        else:
            question = decision.clarifying_question
        outcome = IntakeOutcome(
            status=OutcomeStatus.EMERGENCY_RECOMMENDATION if is_emergency else OutcomeStatus.NEEDS_CLARIFICATION,
            transcript=transcript,
            classification=classification,
            extraction=extraction,
            clarifying_question=question,
            reasons=reasons,
            normalized_transcript=normalized,
            safety_gate_result="emergency_recommendation" if is_emergency else "held_for_clarification",
        )

    # --- Audit: log every outcome, routed or abstained ---
    if audit_log_path is not None:
        log_outcome(outcome, log_path=audit_log_path, session_id=session_id)

    return outcome
