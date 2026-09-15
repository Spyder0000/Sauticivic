"""Sahara v2.5 ASR client with cloud-provider fallbacks.

**How it's used:**
- In the backend (voice intake endpoint): `transcribe_audio(audio_bytes, filename)`
- In the bench runner (bench/models/run_sahara.py): same function, corpus loop

**Fallback logic (non-negotiable — per TASK_SPLIT Week 1 #27):**
If Sahara fails, Deepgram Nova-3 and then Gemini are tried when configured.
No local model is downloaded or loaded by the web application.

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
import base64
import os
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

    Raises on all failures (caller decides whether to try another provider).
    """
    endpoint_url = _resolve_sahara_url(settings.sahara_api_url)
    mime_type = _get_mime_type(filename)

    import os
    api_key = settings.sahara_api_key or os.environ.get("SAHARA_API_KEY", "")

    with httpx.Client(timeout=60.0) as client:
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                resp = client.post(
                    endpoint_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"audio_file_blob": (filename, io.BytesIO(audio_bytes), mime_type)},
                    data={
                        "audio_file_name": filename,
                        "use_language_asr_input": language,
                    },
                )
                if resp.status_code >= 400:
                    # 4xx responses are permanent for this request; retrying only
                    # delays the citizen before the next provider can be tried.
                    detail = resp.text[:500].replace("\n", " ")
                    if 400 <= resp.status_code < 500:
                        raise RuntimeError(f"Sahara rejected the audio ({resp.status_code}): {detail}")
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
            except Exception as exc:
                if isinstance(exc, RuntimeError) and str(exc).startswith("Sahara rejected the audio"):
                    raise
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
# Cloud fallbacks
# ---------------------------------------------------------------------------

def _call_deepgram(audio_bytes: bytes, filename: str) -> ASRResult:
    key = settings.deepgram_api_key or os.environ.get("DEEPGRAM_API_KEY", "")
    if not key:
        raise RuntimeError("DEEPGRAM_API_KEY is not configured")
    response = httpx.post(
        "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&detect_language=true",
        headers={"Authorization": f"Token {key}", "Content-Type": _get_mime_type(filename)},
        content=audio_bytes,
        timeout=30.0,
    )
    response.raise_for_status()
    alternative = response.json()["results"]["channels"][0]["alternatives"][0]
    transcript = (alternative.get("transcript") or "").strip()
    if not transcript:
        raise RuntimeError("Deepgram returned an empty transcript")
    return ASRResult(transcript, None, alternative.get("confidence"), "deepgram")


def _call_gemini(audio_bytes: bytes, filename: str) -> ASRResult:
    key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    payload = {
        "contents": [{"parts": [
            {"text": "Transcribe this audio verbatim. Return only the transcript; preserve Nigerian Pidgin and code-switching."},
            {"inline_data": {"mime_type": _get_mime_type(filename), "data": base64.b64encode(audio_bytes).decode("ascii")}},
        ]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 250},
    }
    response = httpx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-transcribe:generateContent",
        params={"key": key}, json=payload, timeout=30.0,
    )
    response.raise_for_status()
    body = response.json()
    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    transcript = " ".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    if not transcript:
        detail = str(body.get("promptFeedback") or body.get("error") or "no text candidate")[:500]
        raise RuntimeError(f"Gemini returned no transcript ({detail})")
    return ASRResult(transcript, None, None, "gemini")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    language: str = "pcm",
) -> ASRResult:
    """Transcribe audio bytes to text.

    Strategy: Sahara v2.5 -> Deepgram Nova-3 -> Gemini, only when the
    respective server-side provider key is configured.

    The caller (voice endpoint / bench runner) should catch RuntimeError and
    return a SYSTEM_ERROR outcome to the citizen.
    """
    if settings.sahara_api_key or os.environ.get("SAHARA_API_KEY"):
        try:
            result = _call_sahara(audio_bytes, filename, language=language)
            log.info("ASR: Sahara succeeded (lang=%s, conf=%s)", result.language, result.confidence)
            return result
        except Exception as exc:
            log.warning("Sahara failed after retries (%s) — trying cloud fallback.", exc)

    failures: list[str] = []
    for backend, caller in (("Deepgram", _call_deepgram), ("Gemini", _call_gemini)):
        try:
            result = caller(audio_bytes, filename)
            log.info("ASR: %s fallback succeeded", backend)
            return result
        except Exception as exc:  # provider fallback must never mask the next one
            failures.append(f"{backend}: {exc}")
            log.warning("ASR: %s fallback failed (%s)", backend, exc)
    raise RuntimeError("No configured cloud ASR provider succeeded. " + "; ".join(failures))
