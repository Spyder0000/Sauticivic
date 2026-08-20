"""Full benchmark orchestrator — runs all metrics and produces a versioned results file.

Orchestrates:
  1. downstream_accuracy.py — classification-exact, artifact-safe, artifact-corrupted
  2. wer.py — corpus WER per model (reads bench/results/transcripts/<model>/)
  3. run_oracle_comparison.py — ASR-fault vs. reasoning-fault attribution
       - a baseline run (ground-truth as both ASR and oracle input), plus
       - per-model runs fed the model's real ASR transcripts, when available

Writes the combined results to bench/results/vN_results.json (never overwrites
a prior version — picks the next available version number).

WER and per-model oracle attribution degrade gracefully: when no model
transcripts exist yet (e.g. the synthetic text-only corpus), they report
"not_available" instead of failing. The moment the Colab model runners drop
transcripts into bench/results/transcripts/<model>/, both light up with no
code change.

Usage:
    PYTHONPATH=backend python3 -m bench.metrics.run_full_benchmark
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from bench.metrics.downstream_accuracy import run_downstream_accuracy  # noqa: E402
from bench.metrics.run_oracle_comparison import run_oracle_comparison  # noqa: E402
from bench.metrics.wer import corpus_wer  # noqa: E402

# Models we look for under bench/results/transcripts/<model>/. Order defines
# report order. Kept in sync with bench/models/run_<model>.py.
_MODELS = ["sahara", "whisper", "deepgram"]


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


def _load_corpus(corpus_path: Path) -> list[dict]:
    with open(corpus_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _describe_corpus(corpus: list[dict]) -> str:
    """Build the corpus description from the actual data — never hardcoded.

    Hardcoding these counts is exactly how the description drifts out of sync
    with the corpus (which it previously had). Deriving them keeps the results
    file honest about what was actually scored.
    """
    total = len(corpus)
    routed = [c for c in corpus if c.get("expected_outcome") == "routed"]
    abstain = [c for c in corpus if c.get("expected_outcome") == "needs_clarification"]
    by_domain = Counter(c.get("expected_domain") for c in routed)
    domain_str = ", ".join(f"{n} {dom}" for dom, n in sorted(by_domain.items()))
    return (
        f"{total} text-only clips (no real audio). "
        f"{len(routed)} expected-routed ({domain_str}) + "
        f"{len(abstain)} expected-abstain/ambiguous (needs_clarification). "
        "Mock keyword classifier + regex extractor."
    )


def _load_model_transcripts(transcripts_root: Path, model: str) -> dict[str, str]:
    """Return {clip_id: transcript} for one model, or {} if none are on disk.

    Reads the JSON files written by bench/models/run_<model>.py. Absent dir or
    unreadable files degrade to {} (never raises) so the benchmark keeps running.
    """
    model_dir = transcripts_root / model
    if not model_dir.is_dir():
        return {}
    out: dict[str, str] = {}
    for p in sorted(model_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        clip_id = data.get("clip_id", p.stem)
        out[clip_id] = data.get("transcript", "") or ""
    return out


def _run_wer(corpus: list[dict], transcripts_root: Path) -> dict:
    """Compute corpus WER per model against the ground-truth transcripts.

    Degrades gracefully: a model with no transcripts on disk is marked
    not_available rather than failing the whole benchmark.
    """
    ref_by_id = {c["clip_id"]: c["transcript"] for c in corpus}
    per_model: dict[str, dict] = {}
    any_found = False

    for model in _MODELS:
        transcripts = _load_model_transcripts(transcripts_root, model)
        if not transcripts:
            per_model[model] = {
                "status": "not_available",
                "reason": f"no transcripts in {transcripts_root / model}/",
            }
            continue

        any_found = True
        clips = [
            {"clip_id": cid, "hypothesis": transcripts[cid], "reference": ref}
            for cid, ref in ref_by_id.items()
            if cid in transcripts
        ]
        missing = sorted(cid for cid in ref_by_id if cid not in transcripts)
        result = corpus_wer(clips)
        per_model[model] = {
            "status": "ok",
            "corpus_wer": result["corpus_wer"],
            "total_word_count": result["total_word_count"],
            "total_edit_distance": result["total_edit_distance"],
            "total_insertions": result["total_insertions"],
            "total_deletions": result["total_deletions"],
            "total_substitutions": result["total_substitutions"],
            "clips_scored": result["num_clips"],
            "clips_missing": missing,
            "per_clip": result["per_clip"],
        }

    return {
        "status": "ok" if any_found else "not_available",
        "note": (
            None
            if any_found
            else (
                "Synthetic text-only corpus has no audio, so no model transcripts "
                "exist yet. Run the model runners on Colab (they write to "
                f"{transcripts_root}/<model>/), commit them back, then re-run this "
                "benchmark to populate WER."
            )
        ),
        "normalization_caveat": (
            "WER uses a conservative Naija-contraction normalization table "
            "(e.g. no->not, na->is, e->it, dey->is). These expansions are "
            "approximate on code-switched text — a documented scoring choice, "
            "not a defect. See bench/metrics/wer.py and REPORT.md Known Issues."
        ),
        "per_model": per_model,
    }


def _run_oracle_by_model(corpus_path: Path, transcripts_root: Path) -> dict:
    """Per-model oracle comparison fed the model's real ASR transcripts.

    This is what turns asr_fault from "0 by construction" into a real
    ASR-vs-reasoning attribution. Degrades gracefully when no transcripts exist.
    """
    per_model: dict[str, dict] = {}
    any_found = False

    for model in _MODELS:
        transcripts = _load_model_transcripts(transcripts_root, model)
        if not transcripts:
            per_model[model] = {
                "status": "not_available",
                "reason": f"no transcripts in {transcripts_root / model}/",
            }
            continue
        any_found = True
        oracle = run_oracle_comparison(corpus_path, asr_transcripts=transcripts)
        per_model[model] = {"status": "ok", **oracle["summary"]}

    return {
        "status": "ok" if any_found else "not_available",
        "note": (
            None
            if any_found
            else (
                "No model transcripts yet — asr_fault stays 0 by construction "
                "until Colab runs populate bench/results/transcripts/<model>/. "
                "The wiring is in place: this activates automatically once "
                "transcripts exist, no code change needed."
            )
        ),
        "per_model": per_model,
    }


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
    transcripts_root = results_dir / "transcripts"

    corpus = _load_corpus(corpus_path)

    print(f"Corpus: {corpus_path}")
    print(f"Results dir: {results_dir}")
    print(f"Transcripts: {transcripts_root}")
    print()

    # --- Run downstream accuracy ---
    print("Running downstream accuracy...")
    downstream = run_downstream_accuracy(corpus_path)
    print(f"  Done: {downstream['metrics']['total_clips']} clips evaluated")

    # --- Run corpus WER (per model) ---
    print("Running corpus WER (per model)...")
    wer_results = _run_wer(corpus, transcripts_root)
    if wer_results["status"] == "ok":
        for model, r in wer_results["per_model"].items():
            if r["status"] == "ok":
                print(f"  {model}: WER {r['corpus_wer']:.1%} ({r['clips_scored']} clips)")
    else:
        print("  Skipped: no model transcripts on disk yet (synthetic corpus).")

    # --- Run oracle comparison (baseline: ground-truth as both ASR & oracle) ---
    print("Running oracle-vs-ASR comparison (baseline)...")
    oracle = run_oracle_comparison(corpus_path)
    print(f"  Done: {oracle['summary']['total_clips']} clips compared")

    # --- Run oracle comparison (per model, real ASR transcripts) ---
    print("Running oracle-vs-ASR comparison (per model)...")
    oracle_by_model = _run_oracle_by_model(corpus_path, transcripts_root)
    if oracle_by_model["status"] == "ok":
        for model, r in oracle_by_model["per_model"].items():
            if r.get("status") == "ok":
                print(f"  {model}: asr_fault={r['buckets']['asr_fault']}")
    else:
        print("  Skipped: no model transcripts on disk yet (synthetic corpus).")

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
            "notes": _describe_corpus(corpus),
        },
        "downstream_accuracy": downstream["metrics"],
        "wer": wer_results,
        "oracle_comparison": oracle["summary"],
        "oracle_comparison_by_model": oracle_by_model,
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
            "Baseline oracle comparison uses ground-truth as both ASR and oracle input — "
            "asr_fault is 0 by construction. Per-model attribution (oracle_comparison_by_model) "
            "activates automatically once real transcripts exist.",
            "WER normalization expands Naija contractions approximately (no->not, na->is, "
            "e->it, dey->is) — a documented scoring choice, not a defect.",
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

    print(f"\n  Word Error Rate (per model):")
    if wer_results["status"] == "ok":
        for model, r in wer_results["per_model"].items():
            if r["status"] == "ok":
                print(f"    {model}: {r['corpus_wer']:.1%}  ({r['clips_scored']} clips)")
            else:
                print(f"    {model}: not available")
    else:
        print("    not available — no model transcripts yet (synthetic corpus)")

    print(f"\n  Oracle comparison (baseline — ground-truth as both ASR & oracle):")
    for bucket, count in s["buckets"].items():
        print(f"    {bucket}: {count}")

    print(f"\n  Oracle comparison (per model — real ASR):")
    if oracle_by_model["status"] == "ok":
        for model, r in oracle_by_model["per_model"].items():
            if r.get("status") == "ok":
                b = r["buckets"]
                print(
                    f"    {model}: asr_fault={b['asr_fault']} "
                    f"reasoning_fault={b['reasoning_fault']} "
                    f"concordant_correct={b['concordant_correct']}"
                )
            else:
                print(f"    {model}: not available")
    else:
        print("    not available — no model transcripts yet (synthetic corpus)")

    print(f"\n  LIMITATION: {s['limitation']}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run_full_benchmark()
