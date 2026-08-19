"""POST /intake — voice/text entry point for citizen complaints.

Endpoints
---------
POST /intake
    Accept a text complaint and run the full intake pipeline.
    Body: {"text": "..."}

POST /intake/voice
    Accept an audio file upload, transcribe via Sahara v2.5 (or Whisper
    fallback), then run the exact same pipeline as the text path.
    Form field: `audio` (WAV/MP3/OGG, max 25 MB)

Both paths call `run_intake()` — the gate protects both identically.
No separate code path for voice vs. text. Per ARCHITECTURE.md design rule.
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from ..pipeline import run_intake
from ..services.sahara_asr import transcribe_audio

log = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])

_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB hard cap


# ---------------------------------------------------------------------------
# Text intake
# ---------------------------------------------------------------------------

class TextIntakeRequest(BaseModel):
    text: str


@router.post("")
def intake_text(req: TextIntakeRequest) -> dict:
    """Classify + gate a text complaint.

    Returns a ROUTED outcome (domain + artifact) or a NEEDS_CLARIFICATION
    outcome (clarifying question, no artifact).
    """
    outcome = run_intake(req.text)
    return asdict(outcome)


# ---------------------------------------------------------------------------
# Voice intake
# ---------------------------------------------------------------------------

@router.post("/voice")
async def intake_voice(audio: UploadFile) -> dict:
    """Transcribe an audio complaint and run the full intake pipeline.

    The voice path is a thin wrapper: audio → transcript → run_intake().
    The gate, classifier, and extractor are identical to the text path.

    ASR: Sahara v2.5 (if SAHARA_API_KEY is set) with automatic Whisper
    large-v3 fallback. The fallback runs locally for single requests;
    full corpus runs should use bench/models/run_whisper.py on Colab/cloud.
    """
    # --- Size guard ---
    audio_bytes = await audio.read()
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large (max {_MAX_AUDIO_BYTES // 1024 // 1024} MB).",
        )
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    # --- Transcribe ---
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

    # --- Same pipeline as text path ---
    outcome = run_intake(asr_result.transcript)
    result = asdict(outcome)
    # Attach ASR metadata for the audit log / frontend display
    result["asr"] = {
        "backend": asr_result.backend,
        "language": asr_result.language,
        "confidence": asr_result.confidence,
    }
    return result
