"""POST /intake — voice/text entry point for citizen complaints.

Endpoints
---------
POST /intake
    Accept a text complaint and run the full intake pipeline.
    Body: {"text": "..."}
    Response includes a session_id for clarification follow-ups.

POST /intake/voice
    Accept an audio file upload, transcribe via Sahara v2.5 (or Whisper
    fallback), then run the exact same pipeline as the text path.
    Form field: `audio` (WAV/MP3/OGG, max 25 MB)
    Response includes a session_id.

POST /intake/{session_id}/clarify
    Accept a citizen's answer to a clarifying question.
    Body: {"answer": "..."}
    Re-runs the pipeline on the combined context (original + all answers so far).
    Enforces gate_max_clarification_rounds from config.
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..config import settings
from ..pipeline import run_intake
from ..schemas import OutcomeStatus
from ..services.sahara_asr import transcribe_audio
from ..session_store import (
    add_clarification,
    build_combined_transcript,
    create_session,
    get_session,
    record_llm_call,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])

_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB hard cap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _outcome_with_session(outcome, session_id: str) -> dict:
    """Serialize outcome + attach session_id."""
    result = asdict(outcome)
    result["session_id"] = session_id
    return result


# ---------------------------------------------------------------------------
# Text intake
# ---------------------------------------------------------------------------

class TextIntakeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    consent: bool = False


@router.post("")
def intake_text(req: TextIntakeRequest) -> dict:
    """Classify + gate a text complaint.

    Returns a ROUTED outcome (domain + artifact) or a NEEDS_CLARIFICATION
    outcome (clarifying question, no artifact). Always includes a session_id
    for follow-up clarification calls.
    """
    session_id = create_session(req.text)
    outcome = run_intake(req.text, session_id=session_id, allow_llm=req.consent)
    if req.consent:
        record_llm_call(session_id)
    result = _outcome_with_session(outcome, session_id)
    result["consent"] = {"confirmed": req.consent, "scope": "draft intake processing"}
    return result


# ---------------------------------------------------------------------------
# Voice intake
# ---------------------------------------------------------------------------

@router.post("/voice")
async def intake_voice(audio: UploadFile, consent: bool = Form(False)) -> dict:
    """Transcribe an audio complaint and run the full intake pipeline.

    The voice path is a thin wrapper: audio → transcript → run_intake().
    The gate, classifier, and extractor are identical to the text path.

    ASR: Sahara v2.5 (if SAHARA_API_KEY is set) with automatic Whisper
    large-v3 fallback. The fallback runs locally for single requests;
    full corpus runs should use bench/models/run_whisper.py on Colab/cloud.
    """
    audio_bytes = await audio.read()
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large (max {_MAX_AUDIO_BYTES // 1024 // 1024} MB).",
        )
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    filename = audio.filename or "audio.wav"
    try:
        asr_result = transcribe_audio(audio_bytes, filename)
    except RuntimeError as exc:
        log.error("ASR failed for %s: %s", filename, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Speech recognition unavailable: {exc}. Please use text input as a fallback.",
        ) from exc

    log.info(
        "Voice intake: file=%s backend=%s lang=%s transcript_len=%d",
        filename, asr_result.backend, asr_result.language, len(asr_result.transcript),
    )

    session_id = create_session(asr_result.transcript)
    outcome = run_intake(asr_result.transcript, session_id=session_id, allow_llm=consent)
    if consent:
        record_llm_call(session_id)
    result = _outcome_with_session(outcome, session_id)
    result["asr"] = {
        "backend": asr_result.backend,
        "language": asr_result.language,
        "confidence": asr_result.confidence,
    }
    result["consent"] = {"confirmed": consent, "scope": "draft intake processing"}
    return result


# ---------------------------------------------------------------------------
# Clarification endpoint
# ---------------------------------------------------------------------------

class ClarifyRequest(BaseModel):
    answer: str
    consent: bool = False


@router.post("/{session_id}/clarify")
def intake_clarify(session_id: str, req: ClarifyRequest) -> dict:
    """Re-run the pipeline with a citizen's clarification answer.

    Retrieves the prior session state (original transcript + previous answers),
    appends the new answer, and re-runs run_intake() on the combined context.
    The gate makes a fresh decision on each round — it may still abstain if
    the combined context still isn't confident enough.

    Enforces gate_max_clarification_rounds (from config.py). If the final
    permitted answer still cannot be routed, returns a terminal human-review
    outcome so the client stops asking for more clarification.

    Returns the same IntakeOutcome shape as POST /intake, always with the
    same session_id so the frontend can chain calls.
    """
    state = get_session(session_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Sessions are in-memory and reset on server restart.",
        )

    max_rounds = settings.gate_max_clarification_rounds
    if len(state.clarification_rounds) >= max_rounds:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Maximum clarification rounds ({max_rounds}) reached for session '{session_id}'. "
                "Please contact a human advisor for further assistance."
            ),
        )

    # Append this answer and build the combined transcript
    state = add_clarification(session_id, req.answer.strip())
    combined = build_combined_transcript(state)

    log.info(
        "Clarify: session=%s round=%d combined_len=%d",
        session_id, len(state.clarification_rounds), len(combined),
    )

    allow_llm = req.consent and state.llm_call_count < 2
    outcome = run_intake(combined, session_id=session_id, allow_llm=allow_llm)
    if allow_llm:
        record_llm_call(session_id)
    result = _outcome_with_session(outcome, session_id)
    result["clarification_round"] = len(state.clarification_rounds)
    result["rounds_remaining"] = max_rounds - len(state.clarification_rounds)
    if (
        result["rounds_remaining"] == 0
        and outcome.status is OutcomeStatus.NEEDS_CLARIFICATION
    ):
        result["status"] = OutcomeStatus.HUMAN_REVIEW
        result["clarifying_question"] = None
        result["reasons"].append(
            "Automated clarification limit reached; human review is required."
        )
        result["safety_gate_result"] = "human_review_required"
    return result
