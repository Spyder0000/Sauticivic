"""Oracle-vs-ASR comparison — attributes each pipeline failure to ASR or reasoning.

For every corpus clip, runs the pipeline TWICE:
  1. On the "ASR transcript" (in a real benchmark, this would be the model's output)
  2. On the "ground-truth transcript" (the oracle run)

Then classifies every mismatch into one of four buckets:
  - concordant_correct:  both runs agree and are correct
  - concordant_incorrect: both runs agree but are wrong (reasoning fault)
  - asr_fault:  oracle run correct, ASR run wrong (transcription caused it)
  - reasoning_fault: oracle run also wrong (reasoning is the weak point)

LIMITATION (this version): Since there is no real ASR model yet, we use the
ground-truth transcript as BOTH the "ASR" and "oracle" input. This means:
  - asr_fault will always be 0 (by construction)
  - reasoning_fault captures every case where the pipeline disagrees with the
    expected ground truth on a CLEAN transcript
  - The script's bucketing LOGIC is validated even though the ASR-vs-reasoning
    split is not yet meaningful

This limitation is stated explicitly in the output and in v1_results.json.

Usage:
    PYTHONPATH=backend python3 -m bench.metrics.run_oracle_comparison
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.pipeline import run_intake  # noqa: E402


def load_corpus(corpus_path: Path | str) -> list[dict]:
    with open(corpus_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _outcome_matches_expected(outcome, clip: dict) -> bool:
    """Check if a pipeline outcome matches the expected ground truth."""
    expected_outcome = clip["expected_outcome"]
    expected_domain = clip["expected_domain"]

    if expected_outcome == "needs_clarification":
        return outcome.status.value == "needs_clarification"
    elif expected_outcome == "routed":
        return (
            outcome.status.value == "routed"
            and outcome.domain is not None
            and outcome.domain.value == expected_domain
        )
    return False


def compare_clip(clip: dict, asr_transcript: str | None = None) -> dict:
    """Run oracle comparison for a single clip.

    Args:
        clip: Ground-truth clip dict from the corpus.
        asr_transcript: The ASR-produced transcript. If None, uses the
            ground-truth transcript (which makes asr_fault = 0 by construction).
    """
    gt_transcript = clip["transcript"]
    asr_transcript = asr_transcript if asr_transcript is not None else gt_transcript

    # Run 1: "ASR" transcript (or ground-truth if no real ASR)
    asr_outcome = run_intake(asr_transcript)
    asr_correct = _outcome_matches_expected(asr_outcome, clip)

    # Run 2: Oracle (ground-truth transcript)
    oracle_outcome = run_intake(gt_transcript)
    oracle_correct = _outcome_matches_expected(oracle_outcome, clip)

    # Bucketing
    if oracle_correct and asr_correct:
        bucket = "concordant_correct"
    elif oracle_correct and not asr_correct:
        bucket = "asr_fault"
    elif not oracle_correct and not asr_correct:
        bucket = "concordant_incorrect"
    else:
        # oracle wrong, ASR right — unusual but possible
        bucket = "reasoning_fault"

    return {
        "clip_id": clip["clip_id"],
        "expected_domain": clip["expected_domain"],
        "expected_outcome": clip["expected_outcome"],
        "oracle_domain": oracle_outcome.domain.value if oracle_outcome.domain else None,
        "oracle_outcome": oracle_outcome.status.value,
        "oracle_correct": oracle_correct,
        "asr_domain": asr_outcome.domain.value if asr_outcome.domain else None,
        "asr_outcome": asr_outcome.status.value,
        "asr_correct": asr_correct,
        "bucket": bucket,
        "asr_transcript_same_as_gt": (asr_transcript == gt_transcript),
        "notes": clip.get("notes", ""),
    }


def run_oracle_comparison(
    corpus_path: Path | str,
    asr_transcripts: dict[str, str] | None = None,
) -> dict:
    """Run the oracle-vs-ASR comparison across the full corpus.

    Args:
        corpus_path: Path to the ground-truth corpus JSON.
        asr_transcripts: Optional {clip_id: asr_transcript} map. When provided,
            each clip's real ASR transcript is used for the "ASR run" (which is
            what makes asr_fault meaningful). Clips absent from the map fall back
            to the ground-truth transcript (asr == oracle) for that clip. The
            default (None) reproduces the ground-truth-as-both behavior exactly.

    Returns aggregate bucket counts and per-clip details.
    """
    corpus = load_corpus(corpus_path)
    asr_transcripts = asr_transcripts or {}
    results = [
        compare_clip(clip, asr_transcript=asr_transcripts.get(clip["clip_id"]))
        for clip in corpus
    ]

    total = len(results)
    buckets = {
        "concordant_correct": sum(1 for r in results if r["bucket"] == "concordant_correct"),
        "concordant_incorrect": sum(1 for r in results if r["bucket"] == "concordant_incorrect"),
        "asr_fault": sum(1 for r in results if r["bucket"] == "asr_fault"),
        "reasoning_fault": sum(1 for r in results if r["bucket"] == "reasoning_fault"),
    }

    # Abstention correlation: of all gate-triggered abstentions, which were warranted?
    abstentions = [r for r in results if r["oracle_outcome"] == "needs_clarification"]
    warranted_abstentions = sum(
        1 for r in abstentions if r["expected_outcome"] == "needs_clarification"
    )
    unwarranted_abstentions = sum(
        1 for r in abstentions if r["expected_outcome"] == "routed"
    )

    clips_with_real_asr = sum(
        1 for r in results if not r["asr_transcript_same_as_gt"]
    )
    if asr_transcripts:
        limitation = (
            f"Real ASR transcripts supplied for {clips_with_real_asr}/{total} clips; "
            "clips without a supplied transcript fell back to ground-truth "
            "(asr == oracle) for that clip. asr_fault is meaningful for the clips "
            "that had real ASR input."
        )
    else:
        limitation = (
            "No real ASR model — ground-truth transcript used as both ASR and "
            "oracle input. asr_fault is 0 by construction. This run validates the "
            "script's bucketing logic, not a real ASR-vs-reasoning split."
        )

    summary = {
        "total_clips": total,
        "buckets": buckets,
        "clips_with_real_asr": clips_with_real_asr,
        "abstention_correlation": {
            "total_abstentions": len(abstentions),
            "warranted": warranted_abstentions,
            "unwarranted": unwarranted_abstentions,
        },
        "limitation": limitation,
    }

    return {"summary": summary, "per_clip": results}


if __name__ == "__main__":
    corpus = _REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "ground_truth.json"
    result = run_oracle_comparison(corpus)

    print("\n=== Oracle-vs-ASR Comparison ===")
    s = result["summary"]
    print(f"Total clips: {s['total_clips']}")
    print(f"Buckets:")
    for bucket, count in s["buckets"].items():
        print(f"  {bucket}: {count}")
    print(f"\nAbstention correlation:")
    ac = s["abstention_correlation"]
    print(f"  Total abstentions: {ac['total_abstentions']}")
    print(f"  Warranted:         {ac['warranted']}")
    print(f"  Unwarranted:       {ac['unwarranted']}")
    print(f"\nLIMITATION: {s['limitation']}")
