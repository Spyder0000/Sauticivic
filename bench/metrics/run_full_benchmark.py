"""Full benchmark orchestrator — runs all metrics and produces a versioned results file.

Orchestrates:
  1. downstream_accuracy.py — classification-exact, artifact-safe, artifact-corrupted
  2. wer.py — corpus WER per model (reads bench/results/transcripts/<model>/)
  3. run_oracle_comparison.py — ASR-fault vs. reasoning-fault attribution
       - a baseline run (ground-truth as both ASR and oracle input), plus
       - per-model runs fed the model's real ASR transcripts, when available
  4. calibration_analysis.py — confidence calibration (ECE + reliability diagram)
  5. adversarial_stress_test.py — adversarial trap evaluation & harm-avoidance rate
  6. speaker_equity_analysis.py — per-speaker WER and downstream accuracy breakdown

Writes combined results to bench/results/vN_results.json (never overwriting prior runs).
Every analysis degrades gracefully if insufficient data exists.

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
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from bench.metrics.adversarial_stress_test import run_adversarial_stress_test  # noqa: E402
from bench.metrics.calibration_analysis import run_calibration_analysis  # noqa: E402
from bench.metrics.downstream_accuracy import run_downstream_accuracy  # noqa: E402
from bench.metrics.run_oracle_comparison import run_oracle_comparison  # noqa: E402
from bench.metrics.speaker_equity_analysis import run_speaker_equity_analysis  # noqa: E402
from bench.metrics.wer import corpus_wer  # noqa: E402

_MODELS = ["sahara", "whisper", "deepgram", "gemini"]


def _next_version(results_dir: Path) -> int:
    """Find the next available version number (never overwrite prior runs)."""
    existing = sorted(results_dir.glob("v*_results.json"))
    if not existing:
        return 1
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
    total = len(corpus)
    routed = [c for c in corpus if c.get("expected_outcome") == "routed"]
    abstain = [c for c in corpus if c.get("expected_outcome") == "needs_clarification"]
    by_domain = Counter(c.get("expected_domain") for c in routed)
    domain_str = ", ".join(f"{n} {dom}" for dom, n in sorted(by_domain.items()))
    speakers = len(set(c.get("speaker_id", "unspecified") for c in corpus))
    return (
        f"{total} clips across {speakers} speakers. "
        f"{len(routed)} expected-routed ({domain_str}) + "
        f"{len(abstain)} expected-abstain/ambiguous (needs_clarification). "
        "Mock keyword classifier + regex extractor."
    )


def _load_model_transcripts(transcripts_root: Path, model: str) -> dict[str, str]:
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


def _extract_candidate_entities(text: str) -> list[str]:
    """Extract candidate named entities/proper nouns from text as evaluation targets."""
    words = [w.strip(".,;:?!\"'()") for w in text.split()]
    entities = []
    for i, w in enumerate(words):
        if len(w) > 1 and w[0].isupper() and (i > 0 or not w.islower()):
            entities.append(w.lower())
    return list(set(entities))


def _evaluate_entity_recall(hypothesis: str, entities: list[str]) -> float:
    """Calculate recall fraction of target entities surviving in hypothesis."""
    if not entities:
        return 1.0
    hyp_lower = hypothesis.lower()
    found = sum(1 for e in entities if e in hyp_lower)
    return found / len(entities)


def _run_tier_b_eval(tier_b_corpus_path: Path, transcripts_root: Path) -> dict:
    """Evaluate Tier B public dataset clips for WER and entity accuracy only.

    Explicitly skips downstream routing accuracy as Tier B public clips do not
    have municipal infrastructure / legal aid domain annotations.
    """
    if not tier_b_corpus_path.exists():
        return {
            "status": "pending_ingestion",
            "scope": "WER and entity accuracy only (downstream routing intentionally skipped)",
            "clips_count": 0,
            "note": f"Tier B ground truth file not found at {tier_b_corpus_path}. Ingestion pending.",
            "per_model": {m: {"status": "pending_ingestion"} for m in _MODELS},
        }

    try:
        tier_b_clips = _load_corpus(tier_b_corpus_path)
    except Exception as exc:
        return {
            "status": "error",
            "reason": f"Failed to load Tier B corpus: {exc}",
            "clips_count": 0,
            "per_model": {m: {"status": "error"} for m in _MODELS},
        }

    if not tier_b_clips:
        return {
            "status": "pending_ingestion",
            "scope": "WER and entity accuracy only (downstream routing intentionally skipped)",
            "clips_count": 0,
            "note": "Tier B corpus is empty. Run bench/corpus/tier_b_public/ingest_tier_b.py to populate clips.",
            "per_model": {m: {"status": "pending_ingestion"} for m in _MODELS},
        }

    ref_by_id = {c["clip_id"]: c["transcript"] for c in tier_b_clips}
    entities_by_id: dict[str, list[str]] = {}
    for c in tier_b_clips:
        cid = c["clip_id"]
        exp_ent = c.get("expected_entities")
        if isinstance(exp_ent, dict):
            entities_by_id[cid] = [str(v).lower() for v in exp_ent.values()]
        elif isinstance(exp_ent, list):
            entities_by_id[cid] = [str(v).lower() for v in exp_ent]
        else:
            entities_by_id[cid] = _extract_candidate_entities(c.get("transcript", ""))

    per_model: dict[str, dict] = {}
    any_found = False

    for model in _MODELS:
        transcripts = _load_model_transcripts(transcripts_root, model)
        if not transcripts:
            tier_b_model_dir = transcripts_root / "tier_b"
            if tier_b_model_dir.is_dir():
                transcripts = _load_model_transcripts(tier_b_model_dir, model)

        matching_ids = [cid for cid in ref_by_id if cid in transcripts]
        if not matching_ids:
            per_model[model] = {
                "status": "not_available",
                "reason": f"No Tier B transcripts found for {model}",
                "downstream_routing_accuracy": "skipped (Tier B clips lack municipal/legal domain labels)",
            }
            continue

        any_found = True
        clips = [
            {"clip_id": cid, "hypothesis": transcripts[cid], "reference": ref_by_id[cid]}
            for cid in matching_ids
        ]
        wer_res = corpus_wer(clips)

        entity_scores = [
            _evaluate_entity_recall(transcripts[cid], entities_by_id.get(cid, []))
            for cid in matching_ids
        ]
        mean_entity_acc = sum(entity_scores) / len(entity_scores) if entity_scores else 1.0

        by_source: dict[str, list[dict]] = {}
        for c in tier_b_clips:
            cid = c["clip_id"]
            if cid in transcripts:
                src = c.get("dataset_source", "unknown")
                by_source.setdefault(src, []).append({
                    "clip_id": cid,
                    "hypothesis": transcripts[cid],
                    "reference": c["transcript"],
                })

        source_breakdown = {}
        for src, s_clips in by_source.items():
            s_wer = corpus_wer(s_clips)
            s_ent_scores = [
                _evaluate_entity_recall(c["hypothesis"], entities_by_id.get(c["clip_id"], []))
                for c in s_clips
            ]
            source_breakdown[src] = {
                "clips_scored": len(s_clips),
                "corpus_wer": s_wer["corpus_wer"],
                "entity_accuracy": sum(s_ent_scores) / len(s_ent_scores) if s_ent_scores else 1.0,
            }

        per_model[model] = {
            "status": "ok",
            "corpus_wer": wer_res["corpus_wer"],
            "entity_accuracy": mean_entity_acc,
            "clips_scored": len(matching_ids),
            "by_dataset_source": source_breakdown,
            "downstream_routing_accuracy": "skipped (Tier B clips lack municipal/legal domain labels)",
        }

    return {
        "status": "ok" if any_found else "not_available",
        "scope": "WER and entity accuracy only (downstream routing intentionally skipped)",
        "total_clips": len(tier_b_clips),
        "note": (
            "Tier B evaluates acoustic ASR generalization across independently collected data "
            "(AfriSwitch, FLEURS, AfriSpeech). Downstream classification accuracy is intentionally "
            "skipped because public clips lack civic infrastructure and legal aid domain annotations."
        ),
        "per_model": per_model,
    }


def run_full_benchmark(
    corpus_path: Path | str | None = None,
    results_dir: Path | str | None = None,
    adversarial_path: Path | str | None = None,
    tier_b_corpus_path: Path | str | None = None,
) -> dict:
    """Run complete benchmark suite and write results."""
    corpus_path = Path(corpus_path) if corpus_path else (
        _REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "ground_truth.json"
    )
    results_dir = Path(results_dir) if results_dir else (
        _REPO_ROOT / "bench" / "results"
    )
    adversarial_path = Path(adversarial_path) if adversarial_path else (
        _REPO_ROOT / "bench" / "corpus" / "adversarial_cases.json"
    )
    tier_b_corpus_path = Path(tier_b_corpus_path) if tier_b_corpus_path else (
        _REPO_ROOT / "bench" / "corpus" / "tier_b_public" / "ground_truth_tier_b.json"
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    transcripts_root = results_dir / "transcripts"

    corpus = _load_corpus(corpus_path)
    version = _next_version(results_dir)
    timestamp = datetime.now(timezone.utc).isoformat()

    print(f"Corpus:         {corpus_path}")
    print(f"Results dir:    {results_dir}")
    print(f"Transcripts:    {transcripts_root}")
    print(f"Adversarial:    {adversarial_path}")
    print(f"Target Version: v{version}")
    print()

    # --- 1. Downstream accuracy ---
    print("Running downstream accuracy...")
    downstream = run_downstream_accuracy(corpus_path)
    print(f"  Done: {downstream['metrics']['total_clips']} clips evaluated")

    # --- 2. Corpus WER (per model) ---
    print("Running corpus WER (per model)...")
    wer_results = _run_wer(corpus, transcripts_root)
    if wer_results["status"] == "ok":
        for model, r in wer_results["per_model"].items():
            if r["status"] == "ok":
                print(f"  {model}: WER {r['corpus_wer']:.1%} ({r['clips_scored']} clips)")
    else:
        print("  Skipped: no model transcripts on disk yet (synthetic/un-transcribed corpus).")

    # --- 3. Oracle comparison (baseline) ---
    print("Running oracle-vs-ASR comparison (baseline)...")
    oracle = run_oracle_comparison(corpus_path)
    print(f"  Done: {oracle['summary']['total_clips']} clips compared")

    # --- 4. Oracle comparison (per model) ---
    print("Running oracle-vs-ASR comparison (per model)...")
    oracle_by_model = _run_oracle_by_model(corpus_path, transcripts_root)
    if oracle_by_model["status"] == "ok":
        for model, r in oracle_by_model["per_model"].items():
            if r.get("status") == "ok":
                print(f"  {model}: asr_fault={r['buckets']['asr_fault']}")
    else:
        print("  Skipped: no model transcripts on disk yet.")

    # --- 5. Confidence Calibration Analysis ---
    print("Running confidence calibration analysis...")
    plot_path = results_dir / f"calibration_reliability_diagram.png"
    calibration = run_calibration_analysis(
        corpus_path=corpus_path,
        plot_path=plot_path,
    )
    if calibration["status"] == "ok":
        print(f"  Done: ECE = {calibration['ece']:.1%} (across {calibration['total_decisions']} decisions)")
    else:
        print(f"  Degraded: {calibration.get('reason', 'not enough data')}")

    # --- 6. Adversarial Gate Stress-Test ---
    print("Running adversarial gate stress-test suite...")
    adversarial = run_adversarial_stress_test(adversarial_path)
    if adversarial["status"] == "ok":
        print(
            f"  Done: Harm-Avoidance Rate = {adversarial['harm_avoidance_rate']:.1%} "
            f"({adversarial['abstained_safely_count']}/{adversarial['total_cases']} safe, "
            f"{adversarial['high_severity_breaches_count']} breaches)"
        )
    else:
        print(f"  Degraded: {adversarial.get('reason', 'not enough data')}")

    # --- 7. Speaker / Voice Equity Breakdown ---
    print("Running speaker/voice equity analysis...")
    speaker_equity = run_speaker_equity_analysis(
        corpus_path=corpus_path,
        transcripts_root=transcripts_root,
    )
    if speaker_equity["status"] == "ok":
        print(f"  Done: {speaker_equity['total_speakers']} speakers analyzed. Verdict: {speaker_equity['equity_verdict']}")
    else:
        print(f"  Degraded: {speaker_equity.get('reason', 'not enough data')}")

    # --- 8. Tier B Public Dataset Evaluation (WER + Entity Accuracy only) ---
    print("Running Tier B public dataset evaluation (WER + entity accuracy only)...")
    tier_b_results = _run_tier_b_eval(tier_b_corpus_path, transcripts_root)
    if tier_b_results["status"] == "ok":
        print(f"  Done: {tier_b_results['total_clips']} Tier B clips evaluated across {len(tier_b_results['per_model'])} models")
        for model, r in tier_b_results["per_model"].items():
            if r.get("status") == "ok":
                print(f"    {model}: WER {r['corpus_wer']:.1%}, Entity Recall {r['entity_accuracy']:.1%} ({r['clips_scored']} clips)")
    else:
        print(f"  Tier B status: {tier_b_results['status']} ({tier_b_results.get('note', '')[:70]}...)")

    # --- Assemble results ---
    results = {
        "version": f"v{version}",
        "timestamp": timestamp,
        "corpus": {
            "path": str(corpus_path),
            "total_clips": downstream["metrics"]["total_clips"],
            "type": "synthetic_text_only",
            "notes": _describe_corpus(corpus),
        },
        "tier_a": {
            "corpus_type": "tier_a_recorded",
            "total_clips": downstream["metrics"]["total_clips"],
            "downstream_accuracy": downstream["metrics"],
            "wer": wer_results,
            "oracle_comparison": oracle["summary"],
            "oracle_comparison_by_model": oracle_by_model,
            "calibration_analysis": calibration,
            "adversarial_stress_test": adversarial,
            "speaker_equity_analysis": speaker_equity,
        },
        "tier_b": tier_b_results,
        "downstream_accuracy": downstream["metrics"],
        "wer": wer_results,
        "oracle_comparison": oracle["summary"],
        "oracle_comparison_by_model": oracle_by_model,
        "calibration_analysis": calibration,
        "adversarial_stress_test": adversarial,
        "speaker_equity_analysis": speaker_equity,
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
            "Synthetic corpus / un-transcribed audio — no real ASR model transcripts yet on disk.",
            "Mock keyword classifier — confidence derived from keyword hit ratio, not a calibrated LLM.",
            "Mock regex extractor — entity extraction via pattern matching, not NLP.",
            "Baseline oracle comparison uses ground-truth as both ASR and oracle input — "
            "asr_fault is 0 by construction. Per-model attribution (oracle_comparison_by_model) "
            "activates automatically once real transcripts exist.",
            "WER normalization expands Naija contractions approximately (no->not, na->is, "
            "e->it, dey->is) — a documented scoring choice, not a defect.",
            "Threshold τ=0.70 is tuned against the mock classifier; must be re-derived for real backends.",
            "Tier B evaluates WER and entity accuracy only — downstream routing accuracy is intentionally "
            "skipped as public datasets lack civic infrastructure/legal domain labels.",
        ],
    }

    # --- Write results ---
    output_file = results_dir / f"v{version}_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults written to: {output_file}")

    # --- Print comprehensive summary ---
    m = downstream["metrics"]
    s = oracle["summary"]
    print(f"\n{'='*70}")
    print(f"  BENCHMARK RESULTS — {results['version']}")
    print(f"{'='*70}")
    print(f"  Corpus:                {m['total_clips']} clips ({results['corpus']['type']})")
    print(f"  Classification-exact:  {m['classification_exact']:.1%}")
    print(f"  Artifact-safe rate:    {m['artifact_safe_rate']:.1%}")
    print(f"  Artifact-corrupted:    {m['artifact_corrupted_rate']:.1%} (count={m['artifact_corrupted_count']})")
    print(f"  Abstention rate:       {m['abstention_rate']:.1%}")
    print(f"    Correct abstentions: {m['correct_abstention']}")
    print(f"    False abstentions:   {m['false_abstention']}")

    print(f"\n  Confidence Calibration:")
    if calibration["status"] == "ok":
        print(f"    ECE Score:           {calibration['ece']:.1%}")
        print(f"    Interpretation:      {calibration['interpretation']}")
        print(f"    Caveat:              {calibration['note']}")
    else:
        print(f"    not available — {calibration.get('reason')}")

    print(f"\n  Adversarial Stress Test (Harm Avoidance):")
    if adversarial["status"] == "ok":
        print(f"    Harm-Avoidance Rate: {adversarial['harm_avoidance_rate']:.1%} ({adversarial['abstained_safely_count']}/{adversarial['total_cases']} traps abstained)")
        print(f"    High-Severity Alerts: {adversarial['high_severity_breaches_count']}")
        for b in adversarial["high_severity_findings"]:
            print(f"      [BREACH {b['case_id']}] Routed to {b['wrongly_routed_to']}: {b['danger_description']}")
    else:
        print(f"    not available — {adversarial.get('reason')}")

    print(f"\n  Speaker / Voice Equity Breakdown:")
    if speaker_equity["status"] == "ok":
        print(f"    Equity Verdict:      {speaker_equity['equity_verdict']}")
        if speaker_equity.get("is_confounded_with_clip_difficulty"):
            print(f"    ⚠️  Confounding Notice: {speaker_equity['confounding_analysis']}")
        for spk, spk_data in speaker_equity["per_speaker"].items():
            print(f"      Speaker {spk} ({spk_data['total_clips']} clips, {spk_data['ambiguous_percentage']:.1%} ambiguous): Acc={spk_data['classification_exact']:.1%} | Safe={spk_data['artifact_safe_rate']:.1%} | Corrupted={spk_data['artifact_corrupted_rate']:.1%}")
        for flag in speaker_equity["disparity_flags"]:
            print(f"      [{flag['severity']}] {flag['message']}")
    else:
        print(f"    not available — {speaker_equity.get('reason')}")

    print(f"\n  Word Error Rate (per model):")
    if wer_results["status"] == "ok":
        for model, r in wer_results["per_model"].items():
            if r["status"] == "ok":
                print(f"    {model}: {r['corpus_wer']:.1%}  ({r['clips_scored']} clips)")
            else:
                print(f"    {model}: not available")
    else:
        print("    not available — no model transcripts yet (synthetic corpus)")

    print(f"\n  Oracle comparison (baseline):")
    for bucket, count in s["buckets"].items():
        print(f"    {bucket}: {count}")

    print(f"\n  Tier B Public Dataset Results (WER & Entity Accuracy Only):")
    print(f"    Scope: {tier_b_results.get('scope', 'WER and entity accuracy only')}")
    if tier_b_results["status"] == "ok":
        for model, r in tier_b_results["per_model"].items():
            if r.get("status") == "ok":
                print(f"    {model}: WER={r['corpus_wer']:.1%} | Entity Acc={r['entity_accuracy']:.1%} ({r['clips_scored']} clips)")
            else:
                print(f"    {model}: {r.get('reason', 'not available')}")
    else:
        print(f"    Status: {tier_b_results['status']} — {tier_b_results.get('note', '')}")
    print(f"    Methodology Note: Downstream routing accuracy skipped — public clips lack municipal/legal domain labels.")

    print(f"\n  LIMITATION: {s['limitation']}")
    print(f"{'='*70}")

    return results


if __name__ == "__main__":
    run_full_benchmark()
