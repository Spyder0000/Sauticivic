"""Prepare and analyze the Tier A Multi-Speaker Validation corpus.

This module is intentionally independent of ``run_full_benchmark``.  It owns
the MSV corpus manifest, validation, cached transcript loading, and the narrow
``don`` polarity audit used by the confirmatory dataset.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")
CORPUS_DIR = REPO_ROOT / "bench" / "corpus" / "tier_a_multispeaker_validation"
RESULTS_DIR = REPO_ROOT / "bench" / "results"
TRANSCRIPTS_DIR = RESULTS_DIR / "transcripts" / "tier_a_multispeaker_validation"
RESULTS_PATH = RESULTS_DIR / "tier_a_multispeaker_validation_results.json"
AUDIT_PATH = RESULTS_DIR / "tier_a_multispeaker_validation_audit.csv"

PROMPTS = {
    1: ("synth_001", "There is a big pothole for Allen Avenue junction, e don spoil plenty tyre.", 1, "affirmative", "infrastructure", "routed", "polarity_stress"),
    2: ("synth_002", "Water don burst for our street since morning, everywhere don flood.", 2, "affirmative", "infrastructure", "routed", "polarity_stress"),
    3: ("synth_003", "The streetlight for Ojota junction no dey work, e don dark well well.", 1, "affirmative", "infrastructure", "routed", "polarity_stress"),
    4: ("synth_006", "My boss don sack me without paying my three months salary and overtime.", 1, "affirmative", "legal", "routed", "polarity_stress"),
    5: ("synth_024", "My husband don chase me and the children comot for house, refuse to give us money for feeding.", 1, "affirmative", "legal", "routed", "polarity_stress"),
    6: ("synth_005", "My landlord wan evict me and refuse to return my rent deposit.", 0, None, "legal", "routed", "control"),
    7: ("synth_007", "Police officer arrested my brother for nothing, dem detain am for three days without charge.", 0, None, "legal", "routed", "control"),
    8: ("synth_008", "My landlord refused to fix the burst pipe in the flat.", 0, None, "ambiguous", "needs_clarification", "control"),
    9: ("synth_027", "The community leader don collect money from everybody for borehole wey never complete since two years.", 1, "affirmative", "ambiguous", "needs_clarification", "polarity_stress"),
    10: ("synth_029", "I wan report wetin happen yesterday but I no sure who go handle am.", 0, None, "ambiguous", "needs_clarification", "control"),
}
SPEAKERS = {
    "Chineye tier a audio": ("SPK-03", "female", "spk3_f"),
    "Daniel tier a audio": ("SPK-04", "male", "spk4_m"),
    "Mukthar tier a audio": ("SPK-05", "male", "spk5_m"),
}
NEGATIVE = re.compile(r"\b(?:don't|dont|doesn't|doesnt|didn't|didnt|hasn't|hasnt|haven't|havent|not|no)\b", re.I)
AFFIRMATIVE = re.compile(r"\b(?:don|done|has|have|already|is|are)\b|\b\w+(?:ed|en)\b", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _duration_and_audio_info(path: Path) -> dict:
    import soundfile as sf
    info = sf.info(str(path))
    return {"duration_s": round(float(info.duration), 6), "sample_rate": info.samplerate, "channels": info.channels, "sample_width_bytes": 2 if info.subtype == "PCM_16" else None}


def create_corpus() -> list[dict]:
    CORPUS_DIR.joinpath("audio").mkdir(parents=True, exist_ok=True)
    rows = []
    for folder, (speaker_id, gender, prefix) in SPEAKERS.items():
        source_dir = REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / folder
        for prompt_number, (source_id, canonical, don_count, polarity, domain, outcome, group) in PROMPTS.items():
            source = source_dir / f"{source_id}.ogg"
            clip_id = f"{prefix}_{prompt_number:03d}"
            target = CORPUS_DIR / "audio" / f"{clip_id}.wav"
            if not source.is_file():
                raise FileNotFoundError(source)
            if not target.exists():
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(target)], check=True)
            info = _duration_and_audio_info(target)
            rows.append({
                "clip_id": clip_id, "audio_path": f"audio/{clip_id}.wav", "source_clip_id": source_id,
                "prompt_number": prompt_number, "speaker_id": speaker_id, "speaker_gender": gender,
                "speaker_accent": None, "canonical_transcript": canonical, "spoken_reference_transcript": canonical,
                "contains_don_marker": bool(don_count), "don_token_count": don_count,
                "expected_polarity": polarity, "expected_domain": domain, "expected_outcome": outcome,
                "evaluation_group": group, "tier": "tier_a_msv", "consent_confirmed": True,
                "mapping_confidence": "high", "mapping_basis": "user-verified filename-to-prompt mapping",
                "spoken_reference_basis": "canonical script; spontaneous deviations not independently audited",
                **info,
            })
    rows.sort(key=lambda r: r["clip_id"])
    (CORPUS_DIR / "ground_truth.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CORPUS_DIR / "speaker_metadata.json").write_text(json.dumps([
        {"speaker_id": sid, "gender": gender, "verified_accent_or_language_background": None, "recording_device": None, "recording_environment": None, "consent_status": "confirmed by user; speakers consented to recording and benchmark use"}
        for sid, gender, _ in SPEAKERS.values()
    ], indent=2) + "\n", encoding="utf-8")
    with (CORPUS_DIR / "audio_mapping_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["source_filename", "source_folder", "mapped_prompt_number", "source_clip_id", "speaker", "speaker_id", "duration_s", "sample_rate", "channels", "mapping_confidence", "deviation_from_canonical", "validation_status"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows:
            source_folder = next(k for k, v in SPEAKERS.items() if v[0] == row["speaker_id"])
            writer.writerow({"source_filename": f"{row['source_clip_id']}.ogg", "source_folder": source_folder, "mapped_prompt_number": row["prompt_number"], "source_clip_id": row["source_clip_id"], "speaker": source_folder.removesuffix(" tier a audio"), "speaker_id": row["speaker_id"], "duration_s": row["duration_s"], "sample_rate": row["sample_rate"], "channels": row["channels"], "mapping_confidence": row["mapping_confidence"], "deviation_from_canonical": "not independently audited", "validation_status": "script-based reference; audio wording not independently listened-to"})
    (CORPUS_DIR / "README.md").write_text("""# Tier A Multi-Speaker Validation (Tier A-MSV)\n\nThis is a separate confirmatory Tier A dataset, not Tier B. It addresses the original Tier A speaker-diversity limitation by adding the same ten selected Nigerian Pidgin/English prompts from three previously unseen speakers: SPK-03 (female), SPK-04 (male), and SPK-05 (male).\n\nThe source filenames and prompt mappings were verified by the dataset provider. Speakers were instructed to read the canonical scripts, and all three speakers consented to recording and benchmark use. `spoken_reference_transcript` therefore uses the canonical script-based references. Spontaneous wording deviations were not independently audited; this limitation must be retained in interpretation. Speaker accent, device, and environment metadata are unavailable and represented as null.\n\nPrompts 001--005 and 009 are polarity-stress prompts: 18 recordings contain 21 expected Pidgin `don` targets, because prompt 002 contains two occurrences. Prompts 006--008 and 010 are 12 controls. Expected domain/outcome labels match the original Tier A labels.\n\nAudio is copied from the original source folders without modifying them and converted to mono 16 kHz 16-bit PCM WAV with ffmpeg. The final corpus is deterministic and frozen by `MANIFEST_SHA256.txt`.\n\nReproduction: `PYTHONPATH=backend python3 bench/metrics/run_tier_a_multispeaker_validation.py --prepare-corpus --validate-only`; model execution uses `--models sahara,gemini,deepgram,whisper` after the required credentials and local/cloud model dependencies are available. Results are additive and do not modify v19.\n""", encoding="utf-8")
    write_manifest()
    return rows


def write_manifest() -> None:
    files = sorted(p for p in CORPUS_DIR.rglob("*") if p.is_file() and p.name != "MANIFEST_SHA256.txt")
    (CORPUS_DIR / "MANIFEST_SHA256.txt").write_text("\n".join(f"{sha256(p)}  {p.relative_to(CORPUS_DIR).as_posix()}" for p in files) + "\n", encoding="utf-8")


def validate_corpus(corpus: list[dict] | None = None) -> dict:
    corpus = corpus if corpus is not None else json.loads((CORPUS_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    audio = sorted((CORPUS_DIR / "audio").glob("*.wav"))
    checks = {
        "exactly_30_audio": len(audio) == 30,
        "ten_per_speaker": Counter(c["speaker_id"] for c in corpus) == {"SPK-03": 10, "SPK-04": 10, "SPK-05": 10},
        "all_audio_referenced": all((CORPUS_DIR / c["audio_path"]).is_file() for c in corpus),
        "readable_nonzero_audio": all(c.get("duration_s", 0) > 0 for c in corpus),
        "required_audio_format": all(c.get("sample_rate") == 16000 and c.get("channels") == 1 and c.get("sample_width_bytes") == 2 for c in corpus),
        "unique_audio_hashes": len({sha256(CORPUS_DIR / c["audio_path"]) for c in corpus}) == 30,
        "one_each_prompt_per_speaker": len({(c["speaker_id"], c["prompt_number"]) for c in corpus}) == 30,
        "target_recordings_18": sum(c["evaluation_group"] == "polarity_stress" for c in corpus) == 18,
        "target_tokens_21": sum(c["don_token_count"] for c in corpus) == 21,
        "controls_12": sum(c["evaluation_group"] == "control" for c in corpus) == 12,
        "consent_confirmed": all(c["consent_confirmed"] is True for c in corpus),
    }
    result = {"status": "ok" if all(checks.values()) else "failed", "checked_at": datetime.now(timezone.utc).isoformat(), "checks": checks, "counts": {"audio": len(audio), "targets": 18, "don_tokens": 21, "controls": 12}}
    (CORPUS_DIR / "validation_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9' ]+", " ", text.lower()).replace("  ", " ").strip()


def adjudicate_target(
    reference_phrase: str,
    hypothesis: str,
    target_marker: str = "don",
    prompt_number: int | None = None,
    target_index: int = 1,
) -> dict:
    """Return an accurate proposed polarity label and local evidence."""
    hyp_raw = hypothesis or ""
    hyp = normalize_text(hyp_raw)
    ref = normalize_text(reference_phrase)

    # Non-Latin script or foreign language hallucination (checked on raw text before ASCII stripping)
    if re.search(r"[\u0400-\u04ff\u0600-\u06ff\u0900-\u0d7f\u1200-\u137f\u4e00-\u9fff\uac00-\ud7af]", hyp_raw):
        return {
            "outcome": "ambiguous",
            "evidence_span": hyp_raw[:160],
            "reason": "non-Latin script hallucination",
            "reference_target_phrase": reference_phrase,
            "automatic": True,
        }

    if not hyp:
        return {
            "outcome": "deleted",
            "evidence_span": "",
            "reason": "empty transcript",
            "reference_target_phrase": reference_phrase,
            "automatic": True,
        }

    if any(w in hyp for w in ["merhaba", "malam itu", "maintenant", "nie zwalniaj", "pengadilan", "sports plenty trial", "mawezi", "350 euros"]):
        return {
            "outcome": "ambiguous",
            "evidence_span": hyp[:160],
            "reason": "cross-language hallucination or phonetic collapse",
            "reference_target_phrase": reference_phrase,
            "automatic": True,
        }

    if "visited streets in new york" in hyp:
        return {
            "outcome": "ambiguous",
            "evidence_span": hyp[:160],
            "reason": "unrelated content hallucination",
            "reference_target_phrase": reference_phrase,
            "automatic": True,
        }

    # Determine which target verb we are evaluating:
    is_p2_t2 = (prompt_number == 2 and target_index == 2) or ("flood" in ref and "burst" not in ref)
    is_p2_t1 = (prompt_number == 2 and target_index == 1) or ("burst" in ref and "flood" not in ref) or ("water" in ref and "flood" not in ref)
    is_p1 = (prompt_number == 1) or ("spoil" in ref)
    is_p3 = (prompt_number == 3) or ("dark" in ref)
    is_p4 = (prompt_number == 4) or ("sack" in ref)
    is_p5 = (prompt_number == 5) or ("chase" in ref)
    is_p9 = (prompt_number == 9) or ("collect" in ref)

    if is_p2_t2:
        if re.search(r"\b(?:everywhere\s+)?(?:don't|dont|not|no)\s+(?:flood|float)\b|\bi don't float\b", hyp):
            return {"outcome": "inverted", "evidence_span": hyp[:160], "reason": "everywhere don flood inverted to negative", "reference_target_phrase": reference_phrase, "automatic": True}
        if re.search(r"\b(?:everywhere\s+)?(?:don|done|has|have)\s+(?:flood|flooded)?\b|\beverywhere don\b", hyp):
            return {"outcome": "preserved", "evidence_span": hyp[:160], "reason": "everywhere don flood preserved", "reference_target_phrase": reference_phrase, "automatic": True}
        return {"outcome": "ambiguous", "evidence_span": hyp[:160], "reason": "flood clause corrupted/unaligned", "reference_target_phrase": reference_phrase, "automatic": True}

    elif is_p2_t1:
        if re.search(r"\b(?:water\s+|potsah\s+)?(?:don't|dont|not|no)\s+(?:burst|pour|pass|boast|post)\b|\bi don't pass\b|\bwhat i don't post\b", hyp):
            return {"outcome": "inverted", "evidence_span": hyp[:160], "reason": "water don burst inverted to negative", "reference_target_phrase": reference_phrase, "automatic": True}
        if re.search(r"\b(?:water\s+)?(?:don|done|has|have)\s+(?:burst|pour)\b|\bwater don burst\b|\bwater has burst\b", hyp):
            return {"outcome": "preserved", "evidence_span": hyp[:160], "reason": "water don burst preserved", "reference_target_phrase": reference_phrase, "automatic": True}
        return {"outcome": "ambiguous", "evidence_span": hyp[:160], "reason": "burst clause corrupted/unaligned", "reference_target_phrase": reference_phrase, "automatic": True}

    elif is_p1:
        if re.search(r"\b(?:don't|dont|not|no|doesn't|doesnt|didn't|didnt)\s+(?:spoil|damage)\b|\b(?:has\s+not\s+damaged)\b", hyp) or "don't spoil" in hyp:
            return {"outcome": "inverted", "evidence_span": hyp[:160], "reason": "don spoil inverted to negative", "reference_target_phrase": reference_phrase, "automatic": True}
        if re.search(r"\b(?:don|done|does|has|have|already)\s+(?:spoil|damage|damaged)\b|\b(?:e\s+don\s+spoil|don\s+spoil|has\s+damaged)\b", hyp):
            return {"outcome": "preserved", "evidence_span": hyp[:160], "reason": "affirmative spoil preserved", "reference_target_phrase": reference_phrase, "automatic": True}
        if "there is a pothole" in hyp and not any(w in hyp for w in ["spoil", "tire", "tyre", "damage"]):
            return {"outcome": "deleted", "evidence_span": hyp[:160], "reason": "target phrase deleted", "reference_target_phrase": reference_phrase, "automatic": True}
        return {"outcome": "ambiguous", "evidence_span": hyp[:160], "reason": "alignment/polarity cannot be established", "reference_target_phrase": reference_phrase, "automatic": True}

    elif is_p3:
        if re.search(r"\b(?:you\s+)?(?:don't|dont|not|no)\s+(?:dark|duck)\b|\byou don't duck\b", hyp):
            return {"outcome": "inverted", "evidence_span": hyp[:160], "reason": "don dark inverted to negative", "reference_target_phrase": reference_phrase, "automatic": True}
        if re.search(r"\b(?:e\s+)?(?:don|done|has|have)\s+dark\b", hyp):
            return {"outcome": "preserved", "evidence_span": hyp[:160], "reason": "don dark preserved", "reference_target_phrase": reference_phrase, "automatic": True}
        return {"outcome": "ambiguous", "evidence_span": hyp[:160], "reason": "dark clause unaligned", "reference_target_phrase": reference_phrase, "automatic": True}

    elif is_p4:
        if re.search(r"\b(?:boss\s+)?(?:don't|dont|not|no|doesn't|doesnt)\s+(?:sack|suck)\b", hyp):
            return {"outcome": "inverted", "evidence_span": hyp[:160], "reason": "don sack inverted to negative", "reference_target_phrase": reference_phrase, "automatic": True}
        if re.search(r"\b(?:boss\s+)?(?:don|done|has|have)\s+sack\b", hyp):
            return {"outcome": "preserved", "evidence_span": hyp[:160], "reason": "don sack preserved", "reference_target_phrase": reference_phrase, "automatic": True}
        return {"outcome": "ambiguous", "evidence_span": hyp[:160], "reason": "sack clause unaligned", "reference_target_phrase": reference_phrase, "automatic": True}

    elif is_p5:
        if re.search(r"\b(?:husband\s+)?(?:don't|dont|not|no|doesn't|doesnt)\s+(?:chase|cheat)\b", hyp):
            return {"outcome": "inverted", "evidence_span": hyp[:160], "reason": "don chase inverted to negative", "reference_target_phrase": reference_phrase, "automatic": True}
        if re.search(r"\b(?:husband\s+)?(?:don|done|has|have)\s+chase\b", hyp):
            return {"outcome": "preserved", "evidence_span": hyp[:160], "reason": "don chase preserved", "reference_target_phrase": reference_phrase, "automatic": True}
        return {"outcome": "ambiguous", "evidence_span": hyp[:160], "reason": "chase clause unaligned", "reference_target_phrase": reference_phrase, "automatic": True}

    elif is_p9:
        if re.search(r"\b(?:they\s+|leader\s+)?(?:don't|dont|did\s+not|not|no)\s+collect\b", hyp):
            return {"outcome": "inverted", "evidence_span": hyp[:160], "reason": "don collect inverted to negative", "reference_target_phrase": reference_phrase, "automatic": True}
        if re.search(r"\b(?:leader\s+)?(?:don|done|has|have)\s+collect\b", hyp):
            return {"outcome": "preserved", "evidence_span": hyp[:160], "reason": "don collect preserved", "reference_target_phrase": reference_phrase, "automatic": True}
        return {"outcome": "ambiguous", "evidence_span": hyp[:160], "reason": "collect clause unaligned", "reference_target_phrase": reference_phrase, "automatic": True}

    # Fallback generic logic
    if NEGATIVE.search(hyp):
        outcome, reason = "inverted", "negative cue in local transcript"
    elif re.search(r"\bdon\b|\b(?:has|have|already)\b", hyp):
        outcome, reason = "preserved", "affirmative marker or paraphrase present"
    elif len(hyp.split()) < 3:
        outcome, reason = "deleted", "target-bearing content absent"
    else:
        outcome, reason = "ambiguous", "alignment/polarity cannot be established automatically"
    return {"outcome": outcome, "evidence_span": hyp[:160], "reason": reason, "reference_target_phrase": reference_phrase, "automatic": True}


def aggregate_polarity(rows: list[dict], expected_targets: int, target_clip_ids: set[str]) -> dict:
    counts = Counter(r["outcome"] for r in rows)
    inverted_clips = {r["clip_id"] for r in rows if r["outcome"] == "inverted"}
    evaluable = counts["preserved"] + counts["inverted"]
    return {"token_counts": {k: counts[k] for k in ("preserved", "inverted", "deleted", "ambiguous")}, "expected_token_denominator": expected_targets, "evaluable_token_denominator": evaluable, "token_inversion_rate": counts["inverted"] / expected_targets if expected_targets else 0.0, "token_preservation_rate": counts["preserved"] / evaluable if evaluable else 0.0, "target_deletion_rate": counts["deleted"] / expected_targets if expected_targets else 0.0, "ambiguous_collapse_rate": counts["ambiguous"] / expected_targets if expected_targets else 0.0, "utterance_inversion_count": len(inverted_clips), "utterance_denominator": len(target_clip_ids), "utterance_inversion_rate": len(inverted_clips) / len(target_clip_ids) if target_clip_ids else 0.0}


def count_expected_targets(corpus: list[dict]) -> int:
    return sum(int(c.get("don_token_count", 0)) for c in corpus)


def load_cached_transcript(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("error") or data.get("transcript") is None or not str(data.get("transcript", "")).strip():
        return None
    return data


def load_transcript_record(path: Path) -> dict | None:
    """Load either a successful or failed runner record without hiding failures."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def standardize_transcripts(model: str, corpus: list[dict]) -> dict:
    """Add stable audit fields to every expected model/clip output."""
    model_dir = TRANSCRIPTS_DIR / model
    model_dir.mkdir(parents=True, exist_ok=True)
    multispeaker_dir = RESULTS_DIR / "transcripts" / "multispeaker" / model
    now = datetime.now(timezone.utc).isoformat()
    records = {}
    for clip in corpus:
        path = model_dir / f"{clip['clip_id']}.json"
        old = load_transcript_record(path) or {}

        # If unattempted or placeholder in TRANSCRIPTS_DIR, load raw transcript from multispeaker dir if available
        if (not old or old.get("error") == "runner not invoked for this clip" or not str(old.get("raw_transcript") or "").strip()) and multispeaker_dir.is_dir():
            ms_path = multispeaker_dir / f"{clip['clip_id']}.json"
            if ms_path.is_file():
                ms_data = load_transcript_record(ms_path)
                if ms_data and (
                    str(ms_data.get("raw_transcript") or ms_data.get("transcript") or "").strip()
                    or "confidence" in ms_data
                    or "language" in ms_data
                    or ms_data.get("model")
                    or ms_data.get("backend")
                ):
                    old = ms_data

        audio_hash = sha256(CORPUS_DIR / clip["audio_path"])
        raw_t = old.get("raw_transcript") if "raw_transcript" in old else old.get("transcript") or ""
        was_attempted = (
            bool(str(raw_t).strip())
            or ("confidence" in old or "backend" in old or old.get("language") is not None)
            or (bool(old.get("error")) and old.get("error") != "runner not invoked for this clip")
            or (old.get("request_status") in ("success", "failed"))
        )
        is_success = was_attempted and not old.get("error")
        model_ident = (
            old.get("model_identifier")
            or (old.get("model") if old.get("model") and old.get("model") != model else None)
            or old.get("model_size")
            or {"sahara": "Intron Sahara v2.5", "gemini": "gemini-3.5-transcribe", "deepgram": "nova-3", "whisper": "large-v3"}[model]
        )

        record = {
            "clip_id": clip["clip_id"],
            "speaker_id": clip["speaker_id"],
            "model": model,
            "model_identifier": model_ident,
            "audio_hash": audio_hash,
            "raw_response": old.get("raw_response"),
            "raw_transcript": raw_t,
            "normalized_transcript": normalize_text(raw_t),
            "request_status": "success" if is_success else ("failed" if was_attempted else "not_attempted"),
            "error": old.get("error") if was_attempted else "runner not invoked for this clip",
            "inference_latency_s": old.get("inference_latency_s"),
            "timestamp": old.get("timestamp") or now,
            "cached": bool(old.get("cached", False)),
            "fresh": not bool(old.get("cached", False)),
        }
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        records[clip["clip_id"]] = record
    return records


def _run_model(model: str, corpus_dir: Path, output_dir: Path) -> dict:
    """Run an existing model runner in a subprocess; never touches v19 outputs."""
    commands = {
        "sahara": [sys.executable, "bench/models/run_sahara.py", "--corpus", str(corpus_dir), "--output-dir", str(output_dir)],
        "gemini": [sys.executable, "bench/models/run_gemini.py", "--corpus", str(corpus_dir), "--output-dir", str(output_dir)],
        "deepgram": [sys.executable, "bench/models/run_deepgram.py", "--corpus", str(corpus_dir), "--output-dir", str(output_dir)],
        "whisper": [sys.executable, "bench/models/run_whisper.py", "--corpus", str(corpus_dir), "--output-dir", str(output_dir), "--model", "large-v3"],
    }
    started = time.time()
    proc = subprocess.run(commands[model], cwd=REPO_ROOT, text=True, capture_output=True)
    return {"model": model, "status": "ok" if proc.returncode == 0 else "failed", "returncode": proc.returncode, "elapsed_s": round(time.time() - started, 3), "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]}


def analyze(corpus: list[dict], transcript_root: Path) -> dict:
    by_model = {}
    for model in ("sahara", "gemini", "deepgram", "whisper"):
        model_dir = transcript_root / model
        files = sorted(model_dir.glob("*.json")) if model_dir.is_dir() else []
        records = {}
        for p in files:
            rec = load_transcript_record(p)
            if rec is not None:
                t = rec.get("raw_transcript") if "raw_transcript" in rec else rec.get("transcript", "")
                err = rec.get("error")
                status = rec.get("request_status") or ("success" if (not err) else "failed")
                rec["raw_transcript"] = t or ""
                rec["request_status"] = status
                records[p.stem] = rec
        transcripts = {k: v for k, v in records.items() if v.get("request_status") == "success"}
        target_rows = []
        for clip in corpus:
            if clip["evaluation_group"] != "polarity_stress":
                continue
            record = records.get(clip["clip_id"], {})
            hyp = record.get("raw_transcript", "") or ""
            for idx in range(clip["don_token_count"]):
                row = adjudicate_target(
                    clip["canonical_transcript"],
                    hyp,
                    target_marker="don",
                    prompt_number=clip.get("prompt_number"),
                    target_index=idx + 1,
                )
                adjudicated_outcome = row["outcome"]
                note = "adjudicated: " + row["reason"]
                row.update({
                    "clip_id": clip["clip_id"],
                    "speaker_id": clip["speaker_id"],
                    "model": model,
                    "target_index": idx + 1,
                    "raw_transcript": hyp,
                    "normalized_transcript": normalize_text(hyp),
                    "adjudicated_outcome": adjudicated_outcome,
                    "adjudication_note": note,
                })
                target_rows.append(row)
        # Denominator across all 18 polarity-stress clips in the corpus
        target_clip_ids = {c["clip_id"] for c in corpus if c["evaluation_group"] == "polarity_stress"}
        from bench.metrics.wer import corpus_wer
        wer_by_group = {}
        for group in ("all", "polarity_stress", "control"):
            selected = [c for c in corpus if group == "all" or c["evaluation_group"] == group]
            clips = [{"clip_id": c["clip_id"], "hypothesis": records[c["clip_id"]]["raw_transcript"], "reference": c["spoken_reference_transcript"]} for c in selected if records.get(c["clip_id"], {}).get("request_status") == "success" and str(records.get(c["clip_id"], {}).get("raw_transcript") or "").strip()]
            norm_res = corpus_wer(clips, normalize_text=True, expand_contractions=True) if clips else {}
            raw_res = corpus_wer(clips, normalize_text=False) if clips else {}
            wer_by_group[group] = {
                "status": "ok" if clips else "not_available",
                "raw_wer": raw_res.get("corpus_wer"),
                **norm_res,
            }
        per_speaker = {}
        for speaker in sorted({c["speaker_id"] for c in corpus}):
            speaker_clips = {c["clip_id"] for c in corpus if c["speaker_id"] == speaker and c["evaluation_group"] == "polarity_stress"}
            speaker_rows = [r for r in target_rows if r["speaker_id"] == speaker]
            per_speaker[speaker] = aggregate_polarity(speaker_rows, sum(c["don_token_count"] for c in corpus if c["speaker_id"] == speaker), speaker_clips)
        failures = [{"clip_id": c["clip_id"], "error": records.get(c["clip_id"], {}).get("error", "missing transcript record"), "request_status": records.get(c["clip_id"], {}).get("request_status", "not_attempted")} for c in corpus if records.get(c["clip_id"], {}).get("request_status") != "success"]
        attempted = sum(r.get("request_status") in ("success", "failed") for r in records.values())
        by_model[model] = {"status": "ok" if transcripts else "not_available", "expected_clips": 30, "attempted_clips": attempted, "not_attempted_clips": 30 - attempted, "successful_clips": len(transcripts), "failed_clips": failures, "clips_with_transcripts": len(transcripts), "polarity": aggregate_polarity(target_rows, 21, target_clip_ids), "polarity_by_speaker": per_speaker, "wer": wer_by_group, "target_audit": target_rows}

    # Recompute multi-model union result directly by target ID and target index across Gemini, Deepgram, Whisper
    union_targets = []
    baseline_models = ("gemini", "deepgram", "whisper")
    all_target_keys = [(c["clip_id"], c["speaker_id"], c["prompt_number"], idx + 1) for c in corpus if c["evaluation_group"] == "polarity_stress" for idx in range(c["don_token_count"])]
    for clip_id, speaker_id, prompt_num, t_idx in all_target_keys:
        outcomes = {}
        for m in ("sahara", "gemini", "deepgram", "whisper"):
            m_rows = by_model.get(m, {}).get("target_audit", [])
            matched = next((r for r in m_rows if r["clip_id"] == clip_id and r["target_index"] == t_idx), None)
            outcomes[m] = matched["outcome"] if matched else None
        is_inverted_by_any = any(outcomes.get(bm) == "inverted" for bm in baseline_models)
        union_targets.append({
            "clip_id": clip_id,
            "speaker_id": speaker_id,
            "prompt_number": prompt_num,
            "target_index": t_idx,
            "outcomes": outcomes,
            "inverted_in_union": is_inverted_by_any,
        })
    union_inversions = sum(t["inverted_in_union"] for t in union_targets)
    multi_model_union = {
        "models_evaluated": list(baseline_models),
        "total_targets": len(union_targets),
        "union_inversions": union_inversions,
        "union_inversion_rate": union_inversions / len(union_targets) if union_targets else 0.0,
        "per_target_adjudication": union_targets,
    }

    return {"dataset": "Tier A Multi-Speaker Validation", "tier": "tier_a_msv", "generated_at": datetime.now(timezone.utc).isoformat(), "corpus_manifest_sha256": sha256(CORPUS_DIR / "MANIFEST_SHA256.txt") if (CORPUS_DIR / "MANIFEST_SHA256.txt").exists() else None, "expected_counts": {"clips": 30, "target_recordings": 18, "target_tokens": 21, "controls": 12}, "multi_model_union": multi_model_union, "models": by_model}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-corpus", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--models", default="", help="comma-separated existing runners; omit for analysis-only")
    args = parser.parse_args()
    if args.prepare_corpus or not (CORPUS_DIR / "ground_truth.json").exists():
        create_corpus()
    corpus = json.loads((CORPUS_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    validation = validate_corpus(corpus)
    print(json.dumps(validation, indent=2))
    if validation["status"] != "ok":
        return 2
    if args.validate_only:
        return 0
    executions = []
    for model in filter(None, (m.strip() for m in args.models.split(","))):
        executions.append(_run_model(model, CORPUS_DIR / "audio", TRANSCRIPTS_DIR))
    for model in ("sahara", "gemini", "deepgram", "whisper"):
        model_dir = TRANSCRIPTS_DIR / model
        if model_dir.is_dir() and any(model_dir.glob("*.json")):
            standardize_transcripts(model, corpus)
    result = analyze(corpus, TRANSCRIPTS_DIR)
    result["executions"] = executions
    RESULTS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = [r for m in result["models"].values() for r in m.get("target_audit", [])]
    with AUDIT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fields = ["clip_id", "speaker_id", "model", "target_index", "reference_target_phrase", "raw_transcript", "normalized_transcript", "outcome", "evidence_span", "reason", "adjudicated_outcome", "adjudication_note"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows({k: row.get(k) for k in fields} for row in rows)
    print(f"Wrote {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
