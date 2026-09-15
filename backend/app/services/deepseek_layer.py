"""Optional, bounded DeepSeek assistance for intake wording.

The gate decides safety and routing before this service is ever considered.
This layer can only phrase one clarification question or draft a confirmed
artifact. It sends no audio or identity data and has a deterministic fallback.
"""
from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..config import settings

_clarification_cache: dict[tuple[str, str], "ClarificationSuggestion"] = {}
_artifact_cache: dict[tuple[str, str, tuple[tuple[str, str], ...]], "ArtifactDraft"] = {}


class ClarificationSuggestion(BaseModel):
    """The only accepted LLM clarification shape."""

    model_config = ConfigDict(extra="forbid", strict=True)
    needs_clarification: bool
    missing_field: str = Field(min_length=1, max_length=40)
    question: str = Field(min_length=1, max_length=280)
    reason: str = Field(min_length=1, max_length=320)


class ArtifactDraft(BaseModel):
    """A bounded, presentational addition to an already-authorized artifact."""

    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=140)
    summary: str = Field(min_length=1, max_length=500)
    routing_explanation: str = Field(min_length=1, max_length=320)


def deterministic_question(missing_field: str) -> ClarificationSuggestion:
    templates = {
        "location": "Which street, junction, or community is affected?",
        "timeline": "When did this happen?",
        "transcript_confidence": "Please confirm this part of your complaint: [uncertain phrase].",
        "immediate_danger": "Is anyone currently injured or in immediate danger?",
    }
    question = templates.get(missing_field, "Please share one more detail so we can route this safely.")
    return ClarificationSuggestion(
        needs_clarification=True,
        missing_field=missing_field,
        question=question,
        reason=f"{missing_field.replace('_', ' ').capitalize()} is required before this complaint can be safely routed.",
    )


def parse_clarification_response(content: str) -> ClarificationSuggestion | None:
    """Validate untrusted provider output; malformed output never reaches users."""
    if not content or not content.strip():
        return None
    try:
        return ClarificationSuggestion.model_validate_json(content)
    except ValidationError:
        return None


def request_clarification(*, transcript: str, missing_field: str) -> ClarificationSuggestion:
    """Return an LLM suggestion only when configured; otherwise deterministic copy.

    One retry at most, 10s by default. A failure is intentionally indistinguishable
    to the citizen from the normal deterministic fallback.
    """
    fallback = deterministic_question(missing_field)
    cache_key = (transcript, missing_field)
    if cache_key in _clarification_cache:
        return _clarification_cache[cache_key]
    if not settings.deepseek_api_key:
        return fallback

    payload: dict[str, Any] = {
        "model": "deepseek-flash",
        "temperature": 0.1,
        "max_tokens": 250,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Return strict JSON only. Ask one concise civic-intake clarification. Never invent facts or make safety decisions."},
            {"role": "user", "content": json.dumps({"confirmed_transcript": transcript, "missing_field": missing_field})},
        ],
    }
    for _ in range(settings.deepseek_max_retries + 1):
        try:
            response = httpx.post(
                settings.deepseek_api_url,
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json=payload,
                timeout=settings.deepseek_timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = parse_clarification_response(content)
            if parsed is not None:
                _clarification_cache[cache_key] = parsed
                return parsed
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            continue
    return fallback


def _artifact_fallback(*, domain: str, transcript: str, fields: dict[str, str]) -> ArtifactDraft:
    subject = fields.get("complaint_type") or fields.get("grievance_type") or "Citizen report"
    route = "municipal infrastructure services" if domain == "infrastructure" else "legal-aid intake"
    return ArtifactDraft(
        title=subject.capitalize(),
        summary=transcript[:500],
        routing_explanation=f"The deterministic safety gate approved routing to {route} after required details were found.",
    )


def parse_artifact_response(content: str) -> ArtifactDraft | None:
    if not content or not content.strip():
        return None
    try:
        return ArtifactDraft.model_validate_json(content)
    except ValidationError:
        return None


def request_artifact_draft(*, domain: str, transcript: str, fields: dict[str, str]) -> ArtifactDraft:
    """Draft copy only after gate approval and user confirmation.

    The returned text cannot add fields, change destination, or imply dispatch.
    A compact deterministic draft keeps the workflow usable without the provider.
    """
    fallback = _artifact_fallback(domain=domain, transcript=transcript, fields=fields)
    cache_key = (domain, transcript, tuple(sorted(fields.items())))
    if cache_key in _artifact_cache:
        return _artifact_cache[cache_key]
    if not settings.deepseek_api_key:
        return fallback
    payload: dict[str, Any] = {
        "model": "deepseek-flash",
        "temperature": 0.1,
        "max_tokens": 250,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Return strict JSON only with title, summary, routing_explanation. Use only supplied facts. Do not give legal advice, decide emergencies, or claim dispatch."},
            {"role": "user", "content": json.dumps({"domain": domain, "confirmed_transcript": transcript, "approved_fields": fields})},
        ],
    }
    for _ in range(settings.deepseek_max_retries + 1):
        try:
            response = httpx.post(settings.deepseek_api_url, headers={"Authorization": f"Bearer {settings.deepseek_api_key}"}, json=payload, timeout=settings.deepseek_timeout_seconds)
            response.raise_for_status()
            parsed = parse_artifact_response(response.json()["choices"][0]["message"]["content"])
            if parsed is not None:
                _artifact_cache[cache_key] = parsed
                return parsed
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            continue
    return fallback
