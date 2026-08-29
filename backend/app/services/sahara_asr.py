"""Sahara v2.5 (Intron Voice) ASR client with automatic Whisper large-v3 fallback.

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

**Intron Sahara v2.5 API surface (per docs.voice.intron.io):**
- Endpoint (Sync Batch): `settings.sahara_api_url` (default: https://infer.voice.intron.io/file/v1/upload/sync)
- Endpoint (Streaming): `wss://infer.voice.intron.io/stt/v1/stream`
- Auth: `Authorization: Bearer <SAHARA_API_KEY>`
- Request (Sync Batch): multipart/form-data:
    - `audio_file_blob`: audio bytes / file stream
    - `audio_file_name`: filename string
    - `use_language_asr_input`: language code (default "pcm" for Pidgin-English; also supports "yo", "ha", "ig", "en", etc.)
    - `use_category`: "file_category_general" (optional)
- Response (Sync Batch): `{"data": {"audio_transcript": "...", "file_id": "...", "processing_status": "..."}, "status": "Ok"}`
- Streaming Protocol:
    - WebSocket query params: `sample_rate`, `bit_rate`, `num_channels`, `use_language_asr_input`
    - Input messages: `{"message_type": "INPUT_AUDIO_CHUNK", "audio_base_64": "...", "ack_id": 1}`, `{"message_type": "COMMIT"}`
    - Output messages: `SESSION_CREATED`, `AUDIO_CHUCK_ACK`, `PARTIAL_TRANSCRIPT`, `FINAL_TRANSCRIPT`
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
    language: str | None        # e.g. "pcm", "yo", "en"
    confidence: float | None    # 0–1 if the backend reports it, else None
    backend: str                # "sahara" | "whisper" — for the audit log


# ---------------------------------------------------------------------------
# Sahara v2.5 client
# ---------------------------------------------------------------------------

_RETRY_DELAYS = (1.0, 2.0, 4.0)  # exponential back-off, 3 attempts


def _resolve_sahara_url(url: str) -> str:
    """Normalize Sahara / Intron API endpoint URL."""
    url = url.strip().rstrip("/")
    if url == "https://infer.voice.intron.io":
        return f"{url}/file/v1/upload/sync"
    return url


def _get_mime_type(filename: str) -> str:
    """Determine audio MIME type by extension."""
    ext = Path(filename).suffix.lower()
    mimes = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }
    return mimes.get(ext, "audio/wav")


def _call_sahara(audio_bytes: bytes, filename: str, language: str = "pcm") -> ASRResult:
    """POST audio to Intron Sahara v2.5 and return the transcript.

    Raises on all failures (caller decides whether to fall back to Whisper).
    """
    endpoint_url = _resolve_sahara_url(settings.sahara_api_url)
    mime_type = _get_mime_type(filename)

    with httpx.Client(timeout=60.0) as client:
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                resp = client.post(
                    endpoint_url,
                    headers={"Authorization": f"Bearer {settings.sahara_api_key}"},
                    files={"audio_file_blob": (filename, io.BytesIO(audio_bytes), mime_type)},
                    data={
                        "audio_file_name": filename,
                        "use_language_asr_input": language,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract transcript from Intron response structure:
                # {"data": {"audio_transcript": "...", ...}, "status": "Ok"}
                data_obj = data.get("data") if isinstance(data.get("data"), dict) else data
                transcript = data_obj.get("audio_transcript") or data.get("transcript") or ""
                transcript = transcript.strip()

                if not transcript and resp.status_code == 200:
                    log.warning("Sahara returned empty transcript (response: %s)", data)

                return ASRResult(
                    transcript=transcript,
                    language=language,
                    confidence=None,  # Intron sync response does not provide single confidence score
                    backend="sahara",
                )
            except (httpx.HTTPError, KeyError, Exception) as exc:
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

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    language: str = "pcm",
) -> ASRResult:
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
            result = _call_sahara(audio_bytes, filename, language=language)
            log.info("ASR: Sahara succeeded (lang=%s, conf=%s)", result.language, result.confidence)
            return result
        except Exception as exc:
            log.warning("Sahara failed after retries (%s) — falling back to Whisper.", exc)

    log.info("ASR: using Whisper %s fallback", settings.whisper_model_size)
    return _call_whisper(audio_bytes, filename)
