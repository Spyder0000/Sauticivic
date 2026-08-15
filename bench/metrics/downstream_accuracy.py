"""Downstream accuracy — classification-exact / artifact-safe / artifact-corrupted.

Runs every clip in the synthetic corpus through the real pipeline (with real
artifact generation) and scores each outcome against the ground-truth label.

Metrics:
  - classification_exact: pipeline domain matches expected domain
  - artifact_safe: correct artifact generated, OR gate correctly abstained
  - artifact_corrupted: WRONG artifact silently generated (the dangerous case)
  - abstention_rate: fraction of clips where the gate abstained
  - correct_abstention: gate abstained AND expected_outcome was needs_clarification
  - false_abstention: gate abstained but expected_outcome was routed

Usage:
    PYTHONPATH=backend python3 -m bench.metrics.downstream_accuracy
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend to path so we can import the pipeline.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.pipeline import run_intake  # noqa: E402


def load_corpus(corpus_path: Path | str) -> list[dict]:
    """Load the synthetic ground-truth corpus."""
    with open(corpus_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_clip(clip: dict) -> dict:
    """Run a single clip through the pipeline and score it against ground truth."""
    transcript = clip["transcript"]
    expected_domain = clip["expected_domain"]
    expected_outcome = clip["expected_outcome"]

    outcome = run_intake(transcript)

    actual_domain = outcome.domain.value if outcome.domain else None
    actual_outcome = outcome.status.value

    # --- classification_exact ---
    # For ambiguous clips, we don't expect a specific domain — skip this metric.
    if expected_domain in ("infrastructure", "legal"):
        classification_exact = (actual_domain == expected_domain)
    else:
        classification_exact = None  # not scored for ambiguous clips

    # --- artifact_safe ---
    # Safe if: (correct artifact generated) OR (gate correctly abstained on ambiguous)
    if expected_outcome == "routed" and actual_outcome == "routed" and actual_domain == expected_domain:
        artifact_safe = True
        artifact_corrupted = False
    elif expected_outcome == "needs_clarification" and actual_outcome == "needs_clarification":
        artifact_safe = True  # correct abstention
        artifact_corrupted = False
    elif actual_outcome == "needs_clarification" and expected_outcome == "routed":
        artifact_safe = True  # false abstention is safe (conservative), not corrupted
        artifact_corrupted = False
    elif actual_outcome == "routed" and expected_outcome == "needs_clarification":
        # Routed when it should have abstained — check if it's the right domain
        # Since expected is ambiguous, any routing is risky but not necessarily
        # "corrupted" in the same way. We flag it as not-safe.
        artifact_safe = False
        artifact_corrupted = True
    elif actual_outcome == "routed" and actual_domain != expected_domain:
        # Wrong domain, artifact generated — this is the critical failure.
        artifact_safe = False
        artifact_corrupted = True
    else:
        artifact_safe = True
        artifact_corrupted = False

    return {
        "clip_id": clip["clip_id"],
        "transcript": transcript[:80] + "..." if len(transcript) > 80 else transcript,
        "expected_domain": expected_domain,
        "expected_outcome": expected_outcome,
        "actual_domain": actual_domain,
        "actual_outcome": actual_outcome,
        "classification_exact": classification_exact,
        "artifact_safe": artifact_safe,
        "artifact_corrupted": artifact_corrupted,
        "has_artifact": outcome.artifact is not None,
        "artifact_type": outcome.artifact.get("artifact_type") if outcome.artifact else None,
        "notes": clip.get("notes", ""),
    }


def run_downstream_accuracy(corpus_path: Path | str) -> dict:
    """Run the full downstream accuracy evaluation.

    Returns a dict with per-clip results and aggregate metrics.
    """
    corpus = load_corpus(corpus_path)
    results = [evaluate_clip(clip) for clip in corpus]

    # --- Aggregate metrics ---
    total = len(results)
    scored_classification = [r for r in results if r["classification_exact"] is not None]
    routed = [r for r in results if r["actual_outcome"] == "routed"]
    abstained = [r for r in results if r["actual_outcome"] == "needs_clarification"]
    expected_routed = [r for r in results if r["expected_outcome"] == "routed"]
    expected_abstain = [r for r in results if r["expected_outcome"] == "needs_clarification"]

    metrics = {
        "total_clips": total,
        "classification_exact": (
            sum(1 for r in scored_classification if r["classification_exact"])
            / len(scored_classification)
            if scored_classification else 0.0
        ),
        "artifact_safe_rate": (
            sum(1 for r in results if r["artifact_safe"]) / total
        ),
        "artifact_corrupted_rate": (
            sum(1 for r in results if r["artifact_corrupted"]) / total
        ),
        "artifact_corrupted_count": sum(1 for r in results if r["artifact_corrupted"]),
        "abstention_rate": len(abstained) / total,
        "correct_abstention": sum(
            1 for r in results
            if r["actual_outcome"] == "needs_clarification"
            and r["expected_outcome"] == "needs_clarification"
        ),
        "false_abstention": sum(
            1 for r in results
            if r["actual_outcome"] == "needs_clarification"
            and r["expected_outcome"] == "routed"
        ),
        "total_routed": len(routed),
        "total_abstained": len(abstained),
    }

    return {"metrics": metrics, "per_clip": results}


if __name__ == "__main__":
    corpus = _REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "ground_truth.json"
    result = run_downstream_accuracy(corpus)

    print("\n=== Downstream Accuracy Results ===")
    m = result["metrics"]
    print(f"Total clips:             {m['total_clips']}")
    print(f"Classification-exact:    {m['classification_exact']:.1%}")
    print(f"Artifact-safe rate:      {m['artifact_safe_rate']:.1%}")
    print(f"Artifact-corrupted rate: {m['artifact_corrupted_rate']:.1%}  (count={m['artifact_corrupted_count']})")
    print(f"Abstention rate:         {m['abstention_rate']:.1%}")
    print(f"  Correct abstentions:   {m['correct_abstention']}")
    print(f"  False abstentions:     {m['false_abstention']}")

    print("\n--- Per-clip ---")
    for r in result["per_clip"]:
        status = "✓" if r["artifact_safe"] else "✗ CORRUPTED"
        print(f"  {r['clip_id']}: expected={r['expected_outcome']:20s} actual={r['actual_outcome']:20s} {status}")
