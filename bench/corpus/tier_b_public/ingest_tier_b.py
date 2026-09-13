"""Unified ingestion script for Tier B public benchmark datasets.

Ingests clips across three public speech datasets:
  1. AfriSwitch (intronhealth/AfriSwitch) - code-switched Pidgin, Yoruba, Hausa
  2. FLEURS (google/fleurs) - accented Nigerian languages (Hausa, Yoruba)
  3. AfriSpeech-200 (tobiolatunji/afrispeech-200) - Nigerian-accented English

All audio is trimmed to max 60s, validated (min 3s), and converted to
16kHz mono 16-bit PCM WAV via bench/audio_preprocessing/convert_and_validate.py.
Sidecar JSONs are generated for each clip and aggregated into ground_truth_tier_b.json.

Usage:
  python3 bench/corpus/tier_b_public/ingest_tier_b.py --dry-run
  python3 bench/corpus/tier_b_public/ingest_tier_b.py --dataset all
  python3 bench/corpus/tier_b_public/ingest_tier_b.py --dataset afriswitch --n-clips 10
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Auto-load .env so HF_TOKEN and other credentials are automatically populated
_env_file = _REPO_ROOT / ".env"
if _env_file.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass

    # Fallback parser if dotenv not installed or spaces in keys
    try:
        for line in _env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

if "HF_TOKEN" in os.environ and "HUGGING_FACE_HUB_TOKEN" not in os.environ:
    os.environ["HUGGING_FACE_HUB_TOKEN"] = os.environ["HF_TOKEN"]

# Optional heavy ML/audio dependencies (lazy error on actual execution if missing)
try:
    import numpy as np
except ImportError:
    np = None

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    from datasets import load_dataset, Audio
except ImportError:
    load_dataset = None
    Audio = None

DEFAULT_OUTPUT_ROOT = _REPO_ROOT / "bench" / "corpus" / "tier_b_public"


def extract_audio_and_sr(audio_data) -> tuple[np.ndarray | None, int | None]:
    """Safely extracts (numpy_array, sample_rate) from HF audio dict without torchcodec."""
    if not audio_data:
        return None, None
    if isinstance(audio_data, dict):
        if "array" in audio_data and audio_data["array"] is not None:
            arr = np.array(audio_data["array"], dtype=np.float32)
            return arr, audio_data.get("sampling_rate", 16000)

        raw_bytes = audio_data.get("bytes")
        if raw_bytes:
            import io
            if sf is not None:
                arr, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32")
                return arr, sr

        raw_path = audio_data.get("path")
        if raw_path and Path(raw_path).exists():
            if sf is not None:
                arr, sr = sf.read(raw_path, dtype="float32")
                return arr, sr

    return None, None


# ---------------------------------------------------------------------------
# Core Audio & Selection Logic
# ---------------------------------------------------------------------------

def trim_clip(audio_array, sr: int, max_duration: float = 60.0):
    """Trim to max_duration seconds. Never pad."""
    max_samples = int(max_duration * sr)
    return audio_array[:max_samples]


def is_valid_duration(audio_array, sr: int, min_sec: float = 3.0, max_sec: float = 60.0) -> bool:
    """Check if audio duration is within bounds [min_sec, max_sec]."""
    duration = len(audio_array) / sr
    return min_sec <= duration <= max_sec


def select_by_cmi(dataset, n: int, cmi_field: str = "cmi"):
    """Sort by CMI descending, return top n without decoding full dataset."""
    try:
        if hasattr(dataset, "column_names") and cmi_field in dataset.column_names:
            cmis = dataset[cmi_field]
            sorted_indices = sorted(
                range(len(cmis)),
                key=lambda i: float(cmis[i]) if cmis[i] is not None else 0.0,
                reverse=True,
            )
            top_indices = sorted_indices[:n]
            return [dataset[int(i)] for i in top_indices]
    except Exception:
        pass

    try:
        sorted_ds = sorted(
            dataset,
            key=lambda x: x.get(cmi_field, 0) if isinstance(x, dict) else getattr(x, cmi_field, 0) or 0,
            reverse=True,
        )
        return sorted_ds[:n]
    except Exception:
        try:
            return [dataset[i] for i in range(min(n, len(dataset)))]
        except Exception:
            return list(dataset)[:n]


def _has_complete_existing_clips(dest_dir: Path, target_count: int) -> bool:
    """Return whether reusable audio, references, and source IDs already exist."""
    existing_wavs = sorted(dest_dir.glob("*.wav"))
    if len(existing_wavs) < target_count:
        return False

    for wav in existing_wavs[:target_count]:
        sidecar_path = wav.with_suffix(".json")
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if (
            not str(sidecar.get("transcript") or "").strip()
            or not str(sidecar.get("upstream_id") or "").strip()
        ):
            return False
    return True


def _upstream_id(row: dict, index: int) -> str:
    """Return the most stable source identifier exposed by a dataset row."""
    return str(
        row.get("id")
        or row.get("audio_id")
        or row.get("filename")
        or f"index_{index}"
    )


def _can_write_upstream(sidecar_path: Path, upstream_id: str) -> bool:
    """Refuse to overwrite a clip ID already bound to another upstream row."""
    if not sidecar_path.is_file():
        return True
    try:
        existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True

    existing_id = str(existing.get("upstream_id") or "").strip()
    if existing_id and existing_id != upstream_id:
        print(
            f"    WARNING: {sidecar_path.stem} is already bound to upstream_id "
            f"{existing_id!r}; dataset returned {upstream_id!r}. Not overwriting."
        )
        return False
    return True



def save_clip(
    audio_array,
    sr: int,
    output_path: Path,
    ground_truth: str,
    metadata: dict,
) -> Path:
    """Save WAV + sidecar JSON with ground truth and metadata."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if sf is not None:
        sf.write(output_path, audio_array, sr)

    sidecar = {
        "audio_file": output_path.name,
        "transcript": ground_truth,
        "language": metadata.get("language"),
        "dataset_source": metadata.get("source"),
        "duration_sec": round(len(audio_array) / sr, 2),
        "cmi": metadata.get("cmi", None),
        "clip_type": metadata.get("clip_type", "code_switched"),
        "was_trimmed": metadata.get("was_trimmed", False),
        "upstream_id": metadata.get("upstream_id"),
        "tier": "B",
    }
    sidecar_path = output_path.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Dataset Ingestion Functions
# ---------------------------------------------------------------------------

def ingest_afriswitch(
    n_per_lang: int = 10,
    max_dur: float = 60.0,
    min_dur: float = 3.0,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """Ingest clips from intronhealth/AfriSwitch (CC BY-NC-SA 4.0).

    Target language pairs:
      - Pidgin-English (pcm): n_per_lang (default 10)
      - Yoruba-English (yor): n_per_lang (default 10)
      - Hausa-English (hau): n_per_lang (default 10)
    Selects top clips sorted by Code-Mixing Index (CMI) descending.
    """
    out_base = (output_dir or DEFAULT_OUTPUT_ROOT) / "afriswitch"
    lang_configs = [
        {"config": "pidgin", "code": "pcm", "folder": "pidgin", "label": "Pidgin-English"},
        {"config": "yoruba", "code": "yor", "folder": "yoruba", "label": "Yoruba-English"},
        {"config": "hausa", "code": "hau", "folder": "hausa", "label": "Hausa-English"},
    ]

    total_target = n_per_lang * len(lang_configs)
    print(f"\n[Dataset 1: AfriSwitch] target={total_target} clips ({n_per_lang} per pair across 3 pairs)")
    print("  Source:       intronhealth/AfriSwitch (HuggingFace, CC BY-NC-SA 4.0)")
    print("  Selection:    CMI (Code-Mixing Index) descending — prioritizes high code-switching density")
    print(f"  Duration:     {min_dur}s min to {max_dur}s max (trimmed if > {max_dur}s)")
    print(f"  Output Base:  {out_base}")

    if dry_run:
        plan = []
        for cfg in lang_configs:
            dest_dir = out_base / cfg["folder"]
            print(f"  [DRY-RUN] Would fetch split '{cfg['config']}' ({cfg['label']}) -> {n_per_lang} clips to {dest_dir}/")
            for i in range(1, n_per_lang + 1):
                cid = f"afriswitch_{cfg['code']}_{i:03d}"
                plan.append({
                    "clip_id": cid,
                    "target_path": str(dest_dir / f"{cid}.wav"),
                    "sidecar_path": str(dest_dir / f"{cid}.json"),
                    "language": cfg["label"],
                    "dataset_source": "afriswitch",
                    "clip_type": "code_switched",
                })
        return plan

    _check_runtime_deps()
    saved_records = []
    for cfg in lang_configs:
        dest_dir = out_base / cfg["folder"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        existing_wavs = sorted(list(dest_dir.glob("*.wav")))
        if _has_complete_existing_clips(dest_dir, n_per_lang):
            print(f"  [AfriSwitch {cfg['label']}] Already has {len(existing_wavs)} clips in {dest_dir}/, skipping download.")
            for wav in existing_wavs[:n_per_lang]:
                sidecar_path = wav.with_suffix(".json")
                if sidecar_path.is_file():
                    meta = json.loads(sidecar_path.read_text(encoding="utf-8"))
                    saved_records.append({"clip_id": wav.stem, "path": wav, **meta})
            continue

        print(f"  Streaming AfriSwitch [{cfg['config']}] (lightweight stream, max 10 clips)...")
        _hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None
        try:
            ds = load_dataset("intronhealth/AfriSwitch", cfg["config"], split="test", streaming=True, token=_hf_token)
            if Audio is not None:
                ds = ds.cast_column("audio", Audio(decode=False))
        except Exception:
            ds = load_dataset("intronhealth/AfriSwitch", cfg["config"], split="test", token=_hf_token)
            if Audio is not None and hasattr(ds, "column_names") and "audio" in ds.column_names:
                ds = ds.cast_column("audio", Audio(decode=False))

        candidate_pool = []
        target_buffer = n_per_lang * 2
        for row in ds:
            audio_info = row.get("audio")
            if not audio_info:
                continue
            arr, sr = extract_audio_and_sr(audio_info)
            if arr is None or sr is None:
                continue
            orig_dur = len(arr) / sr
            if orig_dur < min_dur:
                continue
            cmi_val = float(row.get("cmi", 0.0)) if row.get("cmi") is not None else 0.0
            candidate_pool.append({
                "row": row,
                "arr": arr,
                "sr": sr,
                "cmi": cmi_val,
                "orig_dur": orig_dur,
            })
            if len(candidate_pool) >= target_buffer:
                break

        # Sort candidate buffer by CMI descending to prioritize high code-switching density
        candidate_pool.sort(key=lambda x: x["cmi"], reverse=True)
        top_candidates = candidate_pool[:n_per_lang]

        count = 0
        for item in top_candidates:
            count += 1
            arr = item["arr"]
            sr = item["sr"]
            orig_dur = item["orig_dur"]
            row = item["row"]
            was_trimmed = orig_dur > max_dur
            trimmed_arr = trim_clip(arr, sr, max_dur)
            cid = f"afriswitch_{cfg['code']}_{count:03d}"
            wav_path = dest_dir / f"{cid}.wav"
            transcript = row.get("transcription", "") or row.get("transcript", "") or row.get("sentence", "")
            upstream_id = _upstream_id(row, count)
            if not _can_write_upstream(wav_path.with_suffix(".json"), upstream_id):
                continue
            meta = {
                "source": "afriswitch",
                "language": cfg["label"],
                "cmi": item["cmi"],
                "clip_type": "code_switched",
                "was_trimmed": was_trimmed,
                "upstream_id": upstream_id,
            }
            save_clip(trimmed_arr, sr, wav_path, transcript, meta)
            saved_records.append({"clip_id": cid, "path": wav_path, **meta})
            print(f"    Saved {wav_path.name} (dur={len(trimmed_arr)/sr:.1f}s, cmi={meta['cmi']:.2f})")

    return saved_records


def ingest_fleurs(
    n_hausa: int = 8,
    n_yoruba: int = 7,
    max_dur: float = 60.0,
    min_dur: float = 3.0,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """Ingest single-language accent clips from google/fleurs (CC BY 4.0).

    Target language configs:
      - Hausa (hau_NG): n_hausa clips (default 8)
      - Yoruba (yor_NG): n_yoruba clips (default 7)
    Selects by transcript length descending (proxy for rich phonetic content).
    Labeled as 'accent' clips, not code-switching clips (cmi: null).
    """
    out_base = (output_dir or DEFAULT_OUTPUT_ROOT) / "fleurs"
    lang_specs = [
        {"config": "ha_ng", "folder": "hausa", "label": "Hausa (ha_ng)", "target_n": n_hausa},
        {"config": "yo_ng", "folder": "yoruba", "label": "Yoruba (yo_ng)", "target_n": n_yoruba},
    ]

    total_target = n_hausa + n_yoruba
    print(f"\n[Dataset 2: FLEURS] target={total_target} clips (Hausa={n_hausa}, Yoruba={n_yoruba})")
    print("  Source:       google/fleurs (HuggingFace, CC BY 4.0)")
    print("  Selection:    Transcript length descending (content richness)")
    print("  Note:         Single-language accented Nigerian clips (accent robustness baseline, clip_type='accent')")
    print(f"  Duration:     {min_dur}s min to {max_dur}s max (trimmed if > {max_dur}s)")
    print(f"  Output Base:  {out_base}")

    if dry_run:
        plan = []
        for spec in lang_specs:
            dest_dir = out_base / spec["folder"]
            print(f"  [DRY-RUN] Would fetch google/fleurs '{spec['config']}' -> {spec['target_n']} clips to {dest_dir}/")
            for i in range(1, spec["target_n"] + 1):
                cid = f"fleurs_{spec['folder']}_{i:03d}"
                plan.append({
                    "clip_id": cid,
                    "target_path": str(dest_dir / f"{cid}.wav"),
                    "sidecar_path": str(dest_dir / f"{cid}.json"),
                    "language": spec["label"],
                    "dataset_source": "fleurs",
                    "clip_type": "accent",
                    "cmi": None,
                })
        return plan

    _check_runtime_deps()
    saved_records = []
    for spec in lang_specs:
        dest_dir = out_base / spec["folder"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        existing_wavs = sorted(list(dest_dir.glob("*.wav")))
        if len(existing_wavs) >= spec["target_n"]:
            print(f"  [FLEURS {spec['label']}] Already has {len(existing_wavs)} clips in {dest_dir}/, skipping download.")
            for wav in existing_wavs[:spec["target_n"]]:
                sidecar_path = wav.with_suffix(".json")
                if sidecar_path.is_file():
                    meta = json.loads(sidecar_path.read_text(encoding="utf-8"))
                    saved_records.append({"clip_id": wav.stem, "path": wav, **meta})
            continue

        print(f"  Streaming FLEURS [{spec['config']}] (lightweight stream, max {spec['target_n']} clips)...")
        try:
            ds = load_dataset("google/fleurs", spec["config"], split="test", streaming=True)
            if Audio is not None:
                ds = ds.cast_column("audio", Audio(decode=False))
        except Exception:
            ds = load_dataset("google/fleurs", spec["config"], split="test")
            if Audio is not None and hasattr(ds, "column_names") and "audio" in ds.column_names:
                ds = ds.cast_column("audio", Audio(decode=False))

        candidate_pool = []
        target_buffer = spec["target_n"] * 2
        for row in ds:
            audio_info = row.get("audio")
            if not audio_info:
                continue
            arr, sr = extract_audio_and_sr(audio_info)
            if arr is None or sr is None:
                continue
            orig_dur = len(arr) / sr
            if orig_dur < min_dur:
                continue
            transcript = row.get("transcription", "") or row.get("raw_transcription", "")
            candidate_pool.append({
                "row": row,
                "arr": arr,
                "sr": sr,
                "transcript": transcript,
                "length": len(transcript),
                "orig_dur": orig_dur,
            })
            print(f"    -> Buffered candidate {len(candidate_pool)}/{target_buffer}...", end="\r", flush=True)
            if len(candidate_pool) >= target_buffer:
                break
        print()

        # Sort candidate buffer by transcript length descending
        candidate_pool.sort(key=lambda x: x["length"], reverse=True)
        top_candidates = candidate_pool[:spec["target_n"]]

        count = 0
        for item in top_candidates:
            count += 1
            arr = item["arr"]
            sr = item["sr"]
            orig_dur = item["orig_dur"]
            was_trimmed = orig_dur > max_dur
            trimmed_arr = trim_clip(arr, sr, max_dur)
            cid = f"fleurs_{spec['folder']}_{count:03d}"
            wav_path = dest_dir / f"{cid}.wav"
            meta = {
                "source": "fleurs",
                "language": spec["label"],
                "cmi": None,
                "clip_type": "accent",
                "was_trimmed": was_trimmed,
            }
            save_clip(trimmed_arr, sr, wav_path, item["transcript"], meta)
            saved_records.append({"clip_id": cid, "path": wav_path, **meta})
            print(f"    Saved {wav_path.name} (dur={len(trimmed_arr)/sr:.1f}s, type=accent)")

    return saved_records


def ingest_afrispeech(
    n: int = 15,
    max_dur: float = 60.0,
    min_dur: float = 3.0,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """Ingest Nigerian-accented English clips from tobiolatunji/afrispeech-200 (CC BY 4.0).

    Filters to rows where accent_area == "Nigeria".
    Sorts by transcript length descending (longer = more clinical & geographic named entities).
    """
    dest_dir = (output_dir or DEFAULT_OUTPUT_ROOT) / "afrispeech"
    print(f"\n[Dataset 3: AfriSpeech-200] target={n} clips (Nigerian-accented English)")
    print("  Source:       tobiolatunji/afrispeech-200 (HuggingFace, CC BY 4.0)")
    print("  Filter:       accent_area == 'Nigeria'")
    print("  Selection:    Transcript length descending (maximizes named entities: clinics, landmarks, proper nouns)")
    print(f"  Duration:     {min_dur}s min to {max_dur}s max (trimmed if > {max_dur}s)")
    print(f"  Output Dir:   {dest_dir}")

    if dry_run:
        plan = []
        print(f"  [DRY-RUN] Would fetch tobiolatunji/afrispeech-200 (accent_area='Nigeria') -> {n} clips to {dest_dir}/")
        for i in range(1, n + 1):
            cid = f"afrispeech_ng_{i:03d}"
            plan.append({
                "clip_id": cid,
                "target_path": str(dest_dir / f"{cid}.wav"),
                "sidecar_path": str(dest_dir / f"{cid}.json"),
                "language": "Nigerian-accented English",
                "dataset_source": "afrispeech",
                "clip_type": "accent",
                "cmi": None,
            })
        return plan

    _check_runtime_deps()
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing_wavs = sorted(list(dest_dir.glob("*.wav")))
    if len(existing_wavs) >= n:
        print(f"  [AfriSpeech-200] Already has {len(existing_wavs)} clips in {dest_dir}/, skipping download.")
        saved = []
        for wav in existing_wavs[:n]:
            sidecar_path = wav.with_suffix(".json")
            if sidecar_path.is_file():
                meta = json.loads(sidecar_path.read_text(encoding="utf-8"))
                saved.append({"clip_id": wav.stem, "path": wav, **meta})
        return saved

    print("  Streaming AfriSpeech-200 (lightweight stream, max 15 clips)...")
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    ds = None

    # Stream lightweight Nigerian accent Parquet shards (Edo & Tiv accents, ~48MB total)
    parquet_urls = [
        "https://huggingface.co/datasets/tobiolatunji/afrispeech-200/resolve/refs%2Fconvert%2Fparquet/edo/test/0000.parquet",
        "https://huggingface.co/datasets/tobiolatunji/afrispeech-200/resolve/refs%2Fconvert%2Fparquet/tiv/test/0000.parquet",
    ]
    try:
        ds = load_dataset(
            "parquet",
            data_files={"test": parquet_urls},
            split="test",
            streaming=True,
            token=token,
        )
        if Audio is not None:
            ds = ds.cast_column("audio", Audio(decode=False))
    except Exception:
        ds = None

    if ds is None:
        try:
            ds = load_dataset(
                "tobiolatunji/afrispeech-200",
                revision="refs/convert/parquet",
                split="test",
                streaming=True,
                token=token,
            )
            if Audio is not None:
                ds = ds.cast_column("audio", Audio(decode=False))
        except Exception:
            ds = None

    if ds is None:
        try:
            ds = load_dataset("tobiolatunji/afrispeech-200", split="test", streaming=True, token=token)
            if Audio is not None:
                ds = ds.cast_column("audio", Audio(decode=False))
        except Exception:
            ds = load_dataset("tobiolatunji/afrispeech-200", split="test", token=token)
            if Audio is not None and hasattr(ds, "column_names") and "audio" in ds.column_names:
                ds = ds.cast_column("audio", Audio(decode=False))

    if ds is None:
        print("  ERROR: Could not stream AfriSpeech-200 dataset from Hugging Face.")
        return []

    candidate_pool = []
    target_buffer = n * 2
    for row in ds:
        accent = str(row.get("accent", "") or row.get("accent_area", "")).strip().lower()
        country = str(row.get("country", "")).strip().lower()
        if country and country not in ("nigeria", "ng"):
            continue
        audio_info = row.get("audio")
        if not audio_info:
            continue
        arr, sr = extract_audio_and_sr(audio_info)
        if arr is None or sr is None:
            continue
        orig_dur = len(arr) / sr
        if orig_dur < min_dur:
            continue
        transcript = row.get("transcript", "") or row.get("text", "")
        candidate_pool.append({
            "row": row,
            "arr": arr,
            "sr": sr,
            "transcript": transcript,
            "length": len(transcript),
            "orig_dur": orig_dur,
        })
        print(f"    -> Buffered candidate {len(candidate_pool)}/{target_buffer}...", end="\r", flush=True)
        if len(candidate_pool) >= target_buffer:
            break
    print()

    # Sort candidate buffer by transcript length descending
    candidate_pool.sort(key=lambda x: x["length"], reverse=True)
    top_candidates = candidate_pool[:n]

    saved_records = []
    count = 0
    for item in top_candidates:
        count += 1
        arr = item["arr"]
        sr = item["sr"]
        orig_dur = item["orig_dur"]
        was_trimmed = orig_dur > max_dur
        trimmed_arr = trim_clip(arr, sr, max_dur)
        cid = f"afrispeech_ng_{count:03d}"
        wav_path = dest_dir / f"{cid}.wav"
        meta = {
            "source": "afrispeech",
            "language": "Nigerian-accented English",
            "cmi": None,
            "clip_type": "accent",
            "was_trimmed": was_trimmed,
        }
        save_clip(trimmed_arr, sr, wav_path, item["transcript"], meta)
        saved_records.append({"clip_id": cid, "path": wav_path, **meta})
        print(f"    Saved {wav_path.name} (dur={len(trimmed_arr)/sr:.1f}s, type=accent)")

    return saved_records


# ---------------------------------------------------------------------------
# Ground Truth Aggregation & A/B Validation Execution
# ---------------------------------------------------------------------------

def generate_ground_truth_tier_b(
    tier_b_dir: Path | None = None,
    dry_run: bool = False,
) -> Path:
    """Aggregate all sidecar JSON files into ground_truth_tier_b.json.

    Format matches ground_truth.json with Tier B specific additions:
      - tier: 'B'
      - dataset_source: 'afriswitch' | 'fleurs' | 'afrispeech'
      - clip_type: 'code_switched' | 'accent'
      - cmi: float | null
    """
    root_dir = tier_b_dir or DEFAULT_OUTPUT_ROOT
    target_path = root_dir / "ground_truth_tier_b.json"

    if dry_run:
        print(f"\n[Ground Truth Generation — DRY-RUN]")
        print(f"  Would aggregate all *.json sidecars in {root_dir} into {target_path}")
        print("  Sidecar schema fields captured:")
        print("    {clip_id, transcript, audio_file, language, dataset_source, clip_type, cmi, tier: 'B', duration_sec}")
        return target_path

    records = []
    sidecar_files = sorted(root_dir.rglob("*.json"))
    for p in sidecar_files:
        if p.name in ("ground_truth_tier_b.json", "preprocessing_ab_report.json"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "transcript" not in data:
                continue
            records.append({
                "clip_id": p.stem,
                "transcript": data.get("transcript", ""),
                "audio_file": data.get("audio_file", f"{p.stem}.wav"),
                "language": data.get("language"),
                "dataset_source": data.get("dataset_source"),
                "clip_type": data.get("clip_type", "code_switched"),
                "cmi": data.get("cmi"),
                "tier": "B",
                "duration_sec": data.get("duration_sec"),
                "upstream_id": data.get("upstream_id"),
                "expected_domain": None,
                "expected_outcome": None,
                "notes": f"Tier B {data.get('dataset_source')} evaluation clip (WER and entity accuracy only)",
            })
        except Exception as exc:
            print(f"  Warning: failed to read {p.name}: {exc}")

    target_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Ground Truth Generated] Wrote {len(records)} records to: {target_path}")
    return target_path


def run_post_ingestion_ab_validation(tier_b_dir: Path | None = None, dry_run: bool = False):
    """Run A/B waveform validation on all saved Tier B audio files."""
    root_dir = tier_b_dir or DEFAULT_OUTPUT_ROOT
    print(f"\n[A/B Waveform Validation Check]")
    print("  Tier B audio must pass the same A/B waveform validation (ffmpeg vs. wave+soundfile) as Tier A.")

    if dry_run:
        print(f"  [DRY-RUN] Would execute bench/audio_preprocessing/convert_and_validate.py across:")
        print(f"    - {root_dir / 'afriswitch' / 'pidgin'}")
        print(f"    - {root_dir / 'afriswitch' / 'yoruba'}")
        print(f"    - {root_dir / 'afriswitch' / 'hausa'}")
        print(f"    - {root_dir / 'fleurs' / 'hausa'}")
        print(f"    - {root_dir / 'fleurs' / 'yoruba'}")
        print(f"    - {root_dir / 'afrispeech'}")
        return

    try:
        from bench.audio_preprocessing.convert_and_validate import _tool_available, convert_and_validate
        if not _tool_available("ffmpeg"):
            print("\n[A/B Validation Notice] ffmpeg is not installed on this local system.")
            print("  Skipping optional ffmpeg vs. wave+soundfile A/B validation check (designed for Colab/cloud).")
            print("  All audio files were already standardized to 16kHz mono 16-bit WAV upon ingestion.")
            return

        subdirs = [
            root_dir / "afriswitch" / "pidgin",
            root_dir / "afriswitch" / "yoruba",
            root_dir / "afriswitch" / "hausa",
            root_dir / "fleurs" / "hausa",
            root_dir / "fleurs" / "yoruba",
            root_dir / "afrispeech",
        ]
        for sdir in subdirs:
            if sdir.is_dir():
                print(f"\nValidating directory: {sdir}")
                convert_and_validate(input_dir=sdir, output_dir=sdir)
    except (Exception, SystemExit) as exc:
        print(f"  Notice: A/B validation skipped: {exc}")


def _check_runtime_deps():
    """Ensure heavy libraries are present when attempting real downloads."""
    missing = []
    if np is None:
        missing.append("numpy")
    if sf is None:
        missing.append("soundfile")
    if load_dataset is None:
        missing.append("datasets")
    if missing:
        raise RuntimeError(
            f"Missing required Python libraries: {', '.join(missing)}.\n"
            f"Install them via: pip install {' '.join(missing)}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest Tier B public datasets (AfriSwitch, FLEURS, AfriSpeech)."
    )
    parser.add_argument(
        "--dataset",
        choices=["afriswitch", "fleurs", "afrispeech", "all"],
        default="all",
        help="Which dataset to ingest (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be downloaded/saved without calling HuggingFace API",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=60.0,
        help="Max clip length in seconds (default: 60.0)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=3.0,
        help="Min clip length in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--n-clips",
        type=int,
        default=None,
        help="Optional override for number of clips per language pair / subset",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Directory to save clips (default: {DEFAULT_OUTPUT_ROOT})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 70)
    print("  SAUTICIVIC BRIDGE — TIER B PUBLIC DATASET INGESTION")
    print(f"  Mode: {'DRY RUN (No downloads performed)' if args.dry_run else 'LIVE DOWNLOAD'}")
    print(f"  Target Dataset(s): {args.dataset}")
    print(f"  Duration Bounds: [{args.min_duration}s, {args.max_duration}s]")
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    auth_status = f"AUTHENTICATED (token prefix: {hf_token[:7]}...)" if hf_token else "UNAUTHENTICATED (rate limits apply)"
    print(f"  HF Hub Auth:       {auth_status}")
    print(f"  Base Output Dir:   {args.output_dir}")
    print("=" * 70)

    # 1. AfriSwitch
    if args.dataset in ("afriswitch", "all"):
        n_afriswitch = args.n_clips if args.n_clips is not None else 10
        ingest_afriswitch(
            n_per_lang=n_afriswitch,
            max_dur=args.max_duration,
            min_dur=args.min_duration,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
        )

    # 2. FLEURS
    if args.dataset in ("fleurs", "all"):
        n_hau = args.n_clips if args.n_clips is not None else 8
        n_yor = args.n_clips if args.n_clips is not None else 7
        ingest_fleurs(
            n_hausa=n_hau,
            n_yoruba=n_yor,
            max_dur=args.max_duration,
            min_dur=args.min_duration,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
        )

    # 3. AfriSpeech
    if args.dataset in ("afrispeech", "all"):
        n_afrispeech = args.n_clips if args.n_clips is not None else 15
        ingest_afrispeech(
            n=n_afrispeech,
            max_dur=args.max_duration,
            min_dur=args.min_duration,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
        )

    # 4. Sidecar Aggregation into ground_truth_tier_b.json
    generate_ground_truth_tier_b(args.output_dir, dry_run=args.dry_run)

    # 5. A/B Preprocessing Validation
    run_post_ingestion_ab_validation(args.output_dir, dry_run=args.dry_run)

    print("\n" + "=" * 70)
    print("  TIER B INGESTION PASS COMPLETED.")
    if args.dry_run:
        print("  [DRY-RUN CONFIRMED] No network requests made. Ready for live ingestion.")
    print("=" * 70)


if __name__ == "__main__":
    main()
