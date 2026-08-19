"""Sahara v2.5 ASR client with automatic Whisper large-v3 fallback.

**How it's used:**
- In the backend (voice intake endpoint): `transcribe_audio(audio_bytes, filename)`
- In the bench runner (bench/models/run_sahara.py): same function, corpus loop

**Fallback logic (non-negotiable — per TASK_SPLIT Week 1 #27):**
If `settings.sahara_api_key` is blank OR the Sahara call fails after retries,
this module falls back to Whisper large-v3 silently. The pipeline never sees
the difference — it just gets a transcript string.

**Compute note (per ARCHITECTURE.md):**
Whisper large-v3 inference is too heavy for the local dev machine. The
fallback here exists so the *backend server* can handle a one-off voice
request without Colab. For full corpus benchmark runs, use
`bench/models/run_whisper.py` on Colab/cloud instead.

**Sahara v2.5 API surface:**
- Endpoint: `settings.sahara_api_url` (default: https://api.sahara.ai/v2.5/transcribe)
- Auth: `Authorization: Bearer <SAHARA_API_KEY>`
- Request: multipart/form-data — field `audio` (file) + field `language_hint` (optional)
- Response: `{"transcript": "...", "language": "...", "confidence": 0.0–1.0}`
- Streaming: v2.5 supports streaming, but we use batch for the benchmark runner.
  Streaming can be added per endpoint requirements without changing the caller.

TODO: Confirm v2.5 endpoint/auth with Sahara once API access is granted.
      The field names above are inferred from the v2 spec — may differ.
"""
from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import NamedTuple

import httpx

from ..config import settings

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

class ASRResult(NamedTuple):
    transcript: str
    language: str | None        # e.g. "en-pidgin", "yo", "en"
    confidence: float | None    # 0–1 if the backend reports it, else None
    backend: str                # "sahara" | "whisper" — for the audit log


# ---------------------------------------------------------------------------
# Sahara v2.5 client
# ---------------------------------------------------------------------------

_RETRY_DELAYS = (1.0, 2.0, 4.0)  # exponential back-off, 3 attempts


def _call_sahara(audio_bytes: bytes, filename: str) -> ASRResult:
    """POST audio to Sahara v2.5 and return the transcript.

    Raises on all failures (caller decides whether to fall back to Whisper).
    """
    with httpx.Client(timeout=60.0) as client:
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                resp = client.post(
                    settings.sahara_api_url,
                    headers={"Authorization": f"Bearer {settings.sahara_api_key}"},
                    files={"audio": (filename, io.BytesIO(audio_bytes), "audio/wav")},
                    data={"language_hint": "en-pidgin"},  # bilingual code-switch hint
                )
                resp.raise_for_status()
                data = resp.json()
                return ASRResult(
                    transcript=data["transcript"],
                    language=data.get("language"),
                    confidence=data.get("confidence"),
                    backend="sahara",
                )
            except (httpx.HTTPError, KeyError) as exc:
                if attempt == len(_RETRY_DELAYS):
                    raise
                log.warning(
                    "Sahara attempt %d/%d failed (%s) — retrying in %.0fs",
                    attempt, len(_RETRY_DELAYS), exc, delay,
                )
                time.sleep(delay)

    # Should never reach here — the loop always raises or returns.
    raise RuntimeError("Sahara: exhausted retries")  # pragma: no cover


# ---------------------------------------------------------------------------
# Whisper large-v3 fallback
# ---------------------------------------------------------------------------

_whisper_model = None  # lazy-loaded on first use


def _load_whisper():
    """Lazy-load Whisper so the import doesn't crash when whisper isn't installed."""
    global _whisper_model  # noqa: PLW0603
    if _whisper_model is None:
        try:
            import whisper  # type: ignore[import]
            log.info("Loading Whisper %s — this may take a moment on first run.", settings.whisper_model_size)
            _whisper_model = whisper.load_model(settings.whisper_model_size)
        except ImportError as exc:
            raise RuntimeError(
                "openai-whisper is not installed and Sahara API key is not set. "
                "Install whisper (`pip install openai-whisper`) or set SAHARA_API_KEY."
            ) from exc
    return _whisper_model


def _call_whisper(audio_bytes: bytes, filename: str) -> ASRResult:
    """Transcribe locally with Whisper large-v3.

    NOTE: This runs on the local machine. For full corpus benchmark runs,
    use bench/models/run_whisper.py on Colab/cloud instead.
    """
    import tempfile

    model = _load_whisper()

    # Whisper needs a file path — write to a temp file.
    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path, task="transcribe")
        return ASRResult(
            transcript=result["text"].strip(),
            language=result.get("language"),
            confidence=None,  # Whisper doesn't expose a single clip-level confidence
            backend="whisper",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> ASRResult:
    """Transcribe audio bytes to text.

    Strategy:
    1. If SAHARA_API_KEY is set → try Sahara v2.5 with exponential back-off.
    2. If Sahara key is missing OR all Sahara retries fail → fall back to Whisper.
    3. If Whisper is not installed and Sahara failed → raise RuntimeError.

    The caller (voice endpoint / bench runner) should catch RuntimeError and
    return a SYSTEM_ERROR outcome to the citizen.
    """
    if settings.sahara_api_key:
        try:
            result = _call_sahara(audio_bytes, filename)
            log.info("ASR: Sahara succeeded (lang=%s, conf=%s)", result.language, result.confidence)
            return result
        except Exception as exc:
            log.warning("Sahara failed after retries (%s) — falling back to Whisper.", exc)

    log.info("ASR: using Whisper %s fallback", settings.whisper_model_size)
    return _call_whisper(audio_bytes, filename)
