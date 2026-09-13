"""Standalone Tier A-MSV polarity analysis entry point."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.metrics.run_tier_a_multispeaker_validation import (  # noqa: E402
    aggregate_polarity,
    adjudicate_target,
    count_expected_targets,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--transcripts", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("bench/results/tier_a_multispeaker_validation_results.json"))
    args = parser.parse_args()
    corpus_path = args.corpus / "ground_truth.json" if args.corpus.is_dir() else args.corpus
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    output = {"dataset": "Tier A Multi-Speaker Validation", "expected_counts": {"clips": len(corpus), "target_recordings": sum(c["evaluation_group"] == "polarity_stress" for c in corpus), "target_tokens": count_expected_targets(corpus), "controls": sum(c["evaluation_group"] == "control" for c in corpus)}, "models": {}}
    audit_rows = []
    for model in ("sahara", "gemini", "deepgram", "whisper"):
        records = {}
        for path in sorted((args.transcripts / model).rglob("*.json")) if (args.transcripts / model).is_dir() else []:
            try:
                records[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        target_rows = []
        target_clip_ids = set()
        for clip in corpus:
            if clip["evaluation_group"] != "polarity_stress":
                continue
            record = records.get(clip["clip_id"], {})
            transcript = record.get("raw_transcript", record.get("transcript", "")) or ""
            if transcript:
                target_clip_ids.add(clip["clip_id"])
            for index in range(clip["don_token_count"]):
                proposed = adjudicate_target(
                    clip["canonical_transcript"],
                    transcript,
                    target_marker="don",
                    prompt_number=clip.get("prompt_number"),
                    target_index=index + 1,
                ) if transcript else {"outcome": None, "evidence_span": "", "reason": record.get("error", "transcript pending"), "reference_target_phrase": f"target {index + 1}", "automatic": False}
                adjudicated_outcome = proposed["outcome"]
                note = "adjudicated: " + proposed["reason"] if proposed["outcome"] else "unadjudicated: no transcript"
                row = {"clip_id": clip["clip_id"], "speaker_id": clip["speaker_id"], "model": model, "target_index": index + 1, "reference_target_phrase": proposed["reference_target_phrase"], "raw_transcript": transcript, "normalized_transcript": record.get("normalized_transcript", transcript), "outcome": proposed["outcome"], "evidence_span": proposed["evidence_span"], "reason": proposed["reason"], "adjudicated_outcome": adjudicated_outcome, "adjudication_note": note}
                target_rows.append(row); audit_rows.append(row)
        per_speaker = {}
        for spk in ("SPK-03", "SPK-04", "SPK-05"):
            spk_rows = [r for r in target_rows if r["speaker_id"] == spk and r["outcome"] is not None]
            spk_clips = {r["clip_id"] for r in spk_rows}
            per_speaker[spk] = aggregate_polarity(spk_rows, sum(c["don_token_count"] for c in corpus if c["speaker_id"] == spk), spk_clips)
        output["models"][model] = {"status": "ok" if target_clip_ids else "pending", "successful_clips": sum(bool(r.get("raw_transcript", r.get("transcript", ""))) for r in records.values()), "polarity": aggregate_polarity([r for r in target_rows if r["outcome"] is not None], 21, target_clip_ids), "polarity_by_speaker": per_speaker, "target_audit_rows": len(target_rows)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    audit_path = args.output.with_name("tier_a_multispeaker_validation_audit.csv")
    with audit_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["clip_id", "speaker_id", "model", "target_index", "reference_target_phrase", "raw_transcript", "normalized_transcript", "outcome", "evidence_span", "reason", "adjudicated_outcome", "adjudication_note"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(audit_rows)
    print("\n" + "=" * 80)
    print("POLARITY INVERSION TABLE (Tier A Multi-Speaker Validation)")
    print("=" * 80)
    print(f"{'Model':<24} | {'SPK-03 (F)':<12} | {'SPK-04 (M)':<12} | {'SPK-05 (M)':<12} | {'Combined Rate':<14}")
    print("-" * 80)
    for model_name, mkey in [("Sahara v2.5", "sahara"), ("Gemini 3.5 Transcribe", "gemini"), ("Deepgram Nova-3", "deepgram"), ("Whisper large-v3", "whisper")]:
        mdata = output["models"].get(mkey, {})
        if mdata.get("status") != "ok":
            print(f"{model_name:<24} | {'N/E':<12} | {'N/E':<12} | {'N/E':<12} | {'N/E (Pending)':<14}")
            continue
        spk_res = mdata.get("polarity_by_speaker", {})
        c3 = spk_res.get("SPK-03", {}).get("token_counts", {})
        c4 = spk_res.get("SPK-04", {}).get("token_counts", {})
        c5 = spk_res.get("SPK-05", {}).get("token_counts", {})
        comb = mdata.get("polarity", {})
        s3_str = f"{c3.get('inverted', 0)}/7 ({c3.get('inverted', 0)/7*100:.1f}%)"
        s4_str = f"{c4.get('inverted', 0)}/7 ({c4.get('inverted', 0)/7*100:.1f}%)"
        s5_str = f"{c5.get('inverted', 0)}/7 ({c5.get('inverted', 0)/7*100:.1f}%)"
        comb_inv = comb.get("token_counts", {}).get("inverted", 0)
        comb_str = f"{comb_inv}/21 ({comb_inv/21*100:.1f}%)"
        print(f"{model_name:<24} | {s3_str:<12} | {s4_str:<12} | {s5_str:<12} | {comb_str:<14}")
    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
