"""Adversarial Gate Stress-Test Suite — probes safety & harm avoidance under deceptive inputs.

IMPORTANT METHODOLOGY CONTEXT:
This test set (bench/corpus/adversarial_cases.json) is intentionally adversarial
and completely separate from the main 30-clip Tier A corpus. It contains
deliberately constructed trap cases that sound single-domain on the surface
(e.g., municipal infrastructure or routine tenancy) but involve high-stakes,
dual-domain, violent, retaliatory, or extortion risks.

Its sole purpose is to stress-test the safety mechanism (the confidence/completeness
abstain gate) specifically, measuring the HARM-AVOIDANCE RATE: what fraction of
these dangerous traps correctly trigger abstention (needs_clarification) rather
than confident, silent auto-routing into the wrong domain artifact.

Any auto-routed case is treated as a HIGH-SEVERITY safety violation.

Usage:
    PYTHONPATH=backend python3 -m bench.metrics.adversarial_stress_test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Add backend to path so we can import the pipeline.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.pipeline import run_intake  # noqa: E402
from app.schemas import OutcomeStatus  # noqa: E402


def evaluate_adversarial_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single adversarial trap case through the intake pipeline."""
    case_id = case["case_id"]
    category = case.get("category", "unspecified")
    transcript = case["transcript"]
    surface_domain = case.get("surface_domain", "ambiguous")
    expected_outcome = case.get("expected_outcome", "needs_clarification")
    danger_if_routed = case.get("danger_if_routed", "Unknown danger")
    trap_mechanism = case.get("trap_mechanism", "")

    outcome = run_intake(transcript)

    actual_status = outcome.status.value
    actual_domain = outcome.domain.value if outcome.domain else None
    confidence = outcome.classification.confidence

    # In adversarial testing, harm is avoided if the system abstained or recommended emergency escalation
    abstained = (actual_status in ("needs_clarification", "emergency_recommendation"))
    harm_avoided = abstained

    # Flag critical failure if system confidently generated an artifact on a trap case
    is_high_severity_breach = not abstained and actual_status == "routed"

    return {
        "case_id": case_id,
        "category": category,
        "transcript": transcript,
        "surface_domain": surface_domain,
        "expected_outcome": expected_outcome,
        "actual_status": actual_status,
        "actual_domain": actual_domain,
        "confidence": round(confidence, 4),
        "harm_avoided": harm_avoided,
        "is_high_severity_breach": is_high_severity_breach,
        "danger_if_routed": danger_if_routed,
        "trap_mechanism": trap_mechanism,
        "reasons": outcome.reasons,
    }


def run_adversarial_stress_test(
    cases_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run full adversarial stress-test suite across all trap cases."""
    cases_path = Path(cases_path) if cases_path else (
        _REPO_ROOT / "bench" / "corpus" / "adversarial_cases.json"
    )

    if not cases_path.exists():
        return {
            "status": "not_available",
            "reason": f"Adversarial corpus file not found: {cases_path}",
            "harm_avoidance_rate": None,
            "total_cases": 0,
            "abstained_safely_count": 0,
            "high_severity_breaches_count": 0,
            "per_case": [],
        }

    with open(cases_path, "r", encoding="utf-8") as f:
        try:
            cases = json.load(f)
        except json.JSONDecodeError as err:
            return {
                "status": "not_available",
                "reason": f"Corrupted JSON in {cases_path}: {err}",
                "harm_avoidance_rate": None,
                "total_cases": 0,
            }

    if not cases:
        return {
            "status": "not_available",
            "reason": f"Empty adversarial corpus: {cases_path}",
            "harm_avoidance_rate": None,
            "total_cases": 0,
        }

    evaluations = [evaluate_adversarial_case(c) for c in cases]

    total = len(evaluations)
    safe_count = sum(1 for e in evaluations if e["harm_avoided"])
    breach_count = sum(1 for e in evaluations if e["is_high_severity_breach"])
    harm_avoidance_rate = safe_count / total if total > 0 else 0.0

    high_severity_findings = [
        {
            "case_id": e["case_id"],
            "category": e["category"],
            "wrongly_routed_to": e["actual_domain"],
            "confidence": e["confidence"],
            "danger_description": e["danger_if_routed"],
            "transcript": e["transcript"],
        }
        for e in evaluations
        if e["is_high_severity_breach"]
    ]

    return {
        "status": "ok",
        "corpus_path": str(cases_path),
        "total_cases": total,
        "abstained_safely_count": safe_count,
        "high_severity_breaches_count": breach_count,
        "harm_avoidance_rate": round(harm_avoidance_rate, 4),
        "high_severity_findings": high_severity_findings,
        "per_case": evaluations,
        "methodology_note": (
            "Intentional trap suite: single-domain cues masking domestic violence, "
            "retaliation, or extortion. Measures whether gate abstains when surface "
            "heuristics are misleading. High-severity breaches must be addressed by "
            "re-tuning extraction and classifier uncertainty."
        ),
    }


if __name__ == "__main__":
    res = run_adversarial_stress_test()
    print("\n" + "=" * 70)
    print("  ADVERSARIAL GATE STRESS-TEST SUITE — HARM AVOIDANCE")
    print("=" * 70)

    if res["status"] != "ok":
        print(f"Status: {res['status']}")
        print(f"Reason: {res['reason']}")
        sys.exit(0)

    print(f"Corpus:                 {res['corpus_path']}")
    print(f"Total Trap Cases:       {res['total_cases']}")
    print(f"Abstained Safely:       {res['abstained_safely_count']} / {res['total_cases']}")
    print(f"Harm-Avoidance Rate:    {res['harm_avoidance_rate']:.1%}")
    print(f"High-Severity Breaches: {res['high_severity_breaches_count']}")

    if res["high_severity_breaches_count"] > 0:
        print("\n" + "!" * 70)
        print("  🚨 HIGH-SEVERITY FINDINGS: DANGEROUS SILENT AUTO-ROUTINGS DETECTED")
        print("!" * 70)
        for b in res["high_severity_findings"]:
            print(f"\n• Case [{b['case_id']}] ({b['category']}):")
            print(f"  Transcript: \"{b['transcript']}\"")
            print(f"  Wrongly Routed Domain: {b['wrongly_routed_to']} (Confidence: {b['confidence']:.2f})")
            print(f"  Harm Impact: {b['danger_description']}")
    else:
        print("\n✓ All adversarial traps successfully caught and abstained by the gate!")

    print("\n--- Per-Case Breakdown ---")
    for e in res["per_case"]:
        tag = "✓ SAFE (Abstained)" if e["harm_avoided"] else f"✗ BREACH (Auto-routed to {e['actual_domain']})"
        print(f"  {e['case_id']:<8} | {e['category']:<35} | {tag}")
    print("=" * 70)
