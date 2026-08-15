"""POST /intake — voice/text entry point for citizen complaints.

The text path is wired to the tested pipeline now. The voice path will call the
Sahara ASR service to produce a transcript, then hand that transcript to the
*same* `run_intake`, so the abstain gate protects both inputs identically.

(Requires `fastapi` + `pydantic`; these are server-only deps and are not needed
to run the pipeline's unit tests.)
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from ..pipeline import run_intake

router = APIRouter(prefix="/intake", tags=["intake"])


class TextIntakeRequest(BaseModel):
    text: str


@router.post("")
def intake_text(req: TextIntakeRequest) -> dict:
    """Classify + gate a text complaint. Returns a ROUTED outcome (with a
    domain) or a NEEDS_CLARIFICATION outcome (with a question to ask back)."""
    outcome = run_intake(req.text)
    return asdict(outcome)
