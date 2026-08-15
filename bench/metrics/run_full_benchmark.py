"""Full benchmark orchestrator — runs all metrics and produces a versioned results file.

Orchestrates:
  1. downstream_accuracy.py — classification-exact, artifact-safe, artifact-corrupted
  2. run_oracle_comparison.py — ASR-fault vs. reasoning-fault attribution

Writes the combined results to bench/results/vN_results.json (never overwrites
a prior version — picks the next available version number).

Usage:
    PYTHONPATH=backend python3 -m bench.metrics.run_full_benchmark
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from bench.metrics.downstream_accuracy import run_downstream_accuracy  # noqa: E402
from bench.metrics.run_oracle_comparison import run_oracle_comparison  # noqa: E402


def _next_version(results_dir: Path) -> int:
    """Find the next available version number (never overwrite prior runs)."""
    existing = sorted(results_dir.glob("v*_results.json"))
    if not existing:
        return 1
    # Extract version numbers from filenames like v1_results.json
    versions = []
    for p in existing:
        try:
            v = int(p.stem.split("_")[0].lstrip("v"))
            versions.append(v)
        except (ValueError, IndexError):
            continue
    return max(versions, default=0) + 1


def run_full_benchmark(
    corpus_path: Path | str | None = None,
    results_dir: Path | str | None = None,
) -> dict:
    """Run the complete benchmark suite and write results.

    Returns the full results dict.
    """
    corpus_path = Path(corpus_path) if corpus_path else (
        _REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "ground_truth.json"
    )
    results_dir = Path(results_dir) if results_dir else (
        _REPO_ROOT / "bench" / "results"
    )
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"Corpus: {corpus_path}")
    print(f"Results dir: {results_dir}")
    print()

    # --- Run downstream accuracy ---
    print("Running downstream accuracy...")
    downstream = run_downstream_accuracy(corpus_path)
    print(f"  Done: {downstream['metrics']['total_clips']} clips evaluated")

    # --- Run oracle comparison ---
    print("Running oracle-vs-ASR comparison...")
    oracle = run_oracle_comparison(corpus_path)
    print(f"  Done: {oracle['summary']['total_clips']} clips compared")

    # --- Assemble results ---
    version = _next_version(results_dir)
    timestamp = datetime.now(timezone.utc).isoformat()

    results = {
        "version": f"v{version}",
        "timestamp": timestamp,
        "corpus": {
            "path": str(corpus_path),
            "total_clips": downstream["metrics"]["total_clips"],
            "type": "synthetic_text_only",
            "notes": (
                "v1 synthetic corpus: 15 text-only clips (no real audio). "
                "9 expected-routed (5 infra, 4 legal), 4 expected-abstain, "
                "2 edge-case/ambiguous. Mock keyword classifier + regex extractor."
            ),
        },
        "downstream_accuracy": downstream["metrics"],
        "oracle_comparison": oracle["summary"],
        "per_clip_downstream": downstream["per_clip"],
        "per_clip_oracle": oracle["per_clip"],
        "pipeline_config": {
            "classifier": "MockKeywordClassifier",
            "extractor": "MockExtractionBackend",
            "gate_min_classification_confidence": 0.70,
            "gate_min_entity_confidence": 0.60,
            "asr_model": "none (text-only input)",
        },
        "known_limitations": [
            "Synthetic corpus — no real recorded audio or real ASR transcription.",
            "Mock keyword classifier — confidence derived from keyword hit ratio, not a calibrated model.",
            "Mock regex extractor — entity extraction via pattern matching, not NLP.",
            "Oracle comparison uses ground-truth as both ASR and oracle input — asr_fault is 0 by construction.",
            "Threshold τ=0.70 is tuned against the mock classifier; must be re-derived for real backends.",
        ],
    }

    # --- Write results (never overwrite) ---
    output_file = results_dir / f"v{version}_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults written to: {output_file}")

    # --- Print summary ---
    m = downstream["metrics"]
    s = oracle["summary"]
    print(f"\n{'='*60}")
    print(f"  BENCHMARK RESULTS — {results['version']}")
    print(f"{'='*60}")
    print(f"  Corpus:                {m['total_clips']} clips ({results['corpus']['type']})")
    print(f"  Classification-exact:  {m['classification_exact']:.1%}")
    print(f"  Artifact-safe rate:    {m['artifact_safe_rate']:.1%}")
    print(f"  Artifact-corrupted:    {m['artifact_corrupted_rate']:.1%} (count={m['artifact_corrupted_count']})")
    print(f"  Abstention rate:       {m['abstention_rate']:.1%}")
    print(f"    Correct abstentions: {m['correct_abstention']}")
    print(f"    False abstentions:   {m['false_abstention']}")
    print(f"\n  Oracle comparison buckets:")
    for bucket, count in s["buckets"].items():
        print(f"    {bucket}: {count}")
    print(f"\n  LIMITATION: {s['limitation']}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run_full_benchmark()
