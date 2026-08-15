"""Classifier agent — infrastructure vs. legal routing decision.

Pluggable like the extractor. The default `MockKeywordClassifier` derives a
confidence from how *one-sided* the keyword evidence is: strongly one-sided
input yields high confidence, and genuinely mixed input ("the council demolished
my shop without notice" — both infra and legal) yields low confidence, which is
exactly what should trip the abstain gate.

The classifier only ever returns INFRASTRUCTURE or LEGAL. Deciding to abstain
(NEEDS_CLARIFICATION) is the gate's job, not the classifier's — kept separate so
the confidence signal stays honest and reusable.
"""
from __future__ import annotations

import re
from typing import Protocol

from ..schemas import ClassificationResult, Domain

_INFRA_KEYWORDS = {
    "pothole", "road", "pipe", "water", "burst", "leak", "power", "electricity",
    "light", "streetlight", "outage", "nepa", "waste", "garbage", "refuse",
    "drainage", "gutter", "sewage", "flood", "blocked", "blockage", "pavement",
}
_LEGAL_KEYWORDS = {
    "landlord", "tenant", "tenancy", "rent", "evict", "eviction", "deposit",
    "employer", "boss", "salary", "wage", "wages", "sack", "sacked", "fired",
    "labour", "labor", "overtime", "police", "officer", "arrest", "arrested",
    "detain", "detained", "harass", "harassment", "assault", "contract", "sue",
}


def _count(text_lower: str, vocab: set[str]) -> int:
    return sum(1 for w in vocab if re.search(rf"\b{re.escape(w)}\b", text_lower))


class ClassifierBackend(Protocol):
    def classify(self, transcript: str) -> ClassificationResult: ...


class MockKeywordClassifier:
    """Deterministic infra-vs-legal classifier. Placeholder for the real model.

    confidence = winning_hits / total_hits  (the margin of victory). No signal
    at all -> confidence 0.0, so the gate abstains rather than guessing.
    """

    def classify(self, transcript: str) -> ClassificationResult:
        low = transcript.lower()
        infra = _count(low, _INFRA_KEYWORDS)
        legal = _count(low, _LEGAL_KEYWORDS)
        total = infra + legal
        scores = {"infrastructure": float(infra), "legal": float(legal)}

        if total == 0:
            return ClassificationResult(
                domain=Domain.INFRASTRUCTURE,  # arbitrary; confidence 0 forces the gate to abstain
                confidence=0.0,
                reasons=["no infrastructure or legal keywords detected"],
                scores=scores,
            )

        if infra >= legal:
            domain, winning = Domain.INFRASTRUCTURE, infra
        else:
            domain, winning = Domain.LEGAL, legal

        confidence = winning / total
        reasons = [
            f"infrastructure keyword hits={infra}, legal keyword hits={legal}",
            f"chose {domain.value} with margin-confidence {confidence:.2f}",
        ]
        return ClassificationResult(domain=domain, confidence=confidence, reasons=reasons, scores=scores)


class ClassifierAgent:
    def __init__(self, backend: ClassifierBackend | None = None) -> None:
        self.backend: ClassifierBackend = backend or MockKeywordClassifier()

    def run(self, transcript: str) -> ClassificationResult:
        return self.backend.classify(transcript)
