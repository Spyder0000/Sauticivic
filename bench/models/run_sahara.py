"""Run Sahara v2.5 over a corpus tier and emit transcripts.

**Compute environment:** This script is designed to run on Google Colab or
cloud, NOT on the local dev machine. Sahara API calls are made here.
See ARCHITECTURE.md § Compute Environment.

Output
------
Writes one JSON file per audio clip to --output-dir:
    <output-dir>/sahara/<clip_id>.json
    {
        "clip_id": "...",
        "audio_file": "...",
        "transcript": "...",
        "language": "...",
        "confidence": 0.0–1.0,
        "backend": "sahara",
        "error": null  # or error message if transcription failed
    }

Usage (on Colab / cloud):
    # Set env var first:
    export SAHARA_API_KEY=your_key_here

    python3 bench/models/run_sahara.py \\
        --corpus bench/corpus/tier_a_recorded/audio \\
        --output-dir bench/results/transcripts \\
        [--dry-run]          # print plan without making API calls
        [--delay-ms 200]     # ms between clips (rate limiting)
        [--clip-id synth_001]  # run a single clip only

After running, commit bench/results/transcripts/sahara/ back to the repo.
Metric scripts (wer.py, downstream_accuracy.py) then run locally.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo path setup (works both locally and on Colab after repo clone)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.sahara_asr import transcribe_audio  # noqa: E402

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}


# ---------------------------------------------------------------------------
# Corpus discovery
# ---------------------------------------------------------------------------

def discover_audio_files(corpus_dir: Path, clip_id: str | None = None) -> list[Path]:
    """Return all audio files in corpus_dir, optionally filtered to one clip."""
    files = sorted(
        p for p in corpus_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _AUDIO_EXTENSIONS
    )
    if clip_id:
        files = [f for f in files if f.stem == clip_id]
    return files


# ---------------------------------------------------------------------------
# Single-clip transcription
# ---------------------------------------------------------------------------

def transcribe_clip(audio_path: Path) -> dict:
    """Transcribe one audio file via Sahara. Returns a result dict."""
    try:
        audio_bytes = audio_path.read_bytes()
        result = transcribe_audio(audio_bytes, filename=audio_path.name)
        return {
            "clip_id": audio_path.stem,
            "audio_file": str(audio_path.name),
            "transcript": result.transcript,
            "language": result.language,
            "confidence": result.confidence,
            "backend": result.backend,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "clip_id": audio_path.stem,
            "audio_file": str(audio_path.name),
            "transcript": "",
            "language": None,
            "confidence": None,
            "backend": "sahara",
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_sahara(
    corpus_dir: Path,
    output_dir: Path,
    delay_ms: int = 200,
    dry_run: bool = False,
    clip_id: str | None = None,
) -> list[dict]:
    """Run Sahara over all audio clips in corpus_dir.

    Args:
        corpus_dir: Directory containing audio files.
        output_dir: Root output dir. Transcripts go to output_dir/sahara/.
        delay_ms:   Milliseconds to wait between clips (rate limiting).
        dry_run:    If True, print plan without making API calls.
        clip_id:    If set, only process this one clip.

    Returns:
        List of result dicts (one per clip).
    """
    sahara_out = output_dir / "sahara"
    audio_files = discover_audio_files(corpus_dir, clip_id)

    if not audio_files:
        print(f"No audio files found in {corpus_dir}")
        return []

    print(f"Corpus dir:  {corpus_dir}")
    print(f"Output dir:  {sahara_out}")
    print(f"Clips found: {len(audio_files)}")
    print(f"Delay:       {delay_ms}ms between clips")
    if dry_run:
        print("\n[DRY RUN] — no API calls will be made.\n")

    if dry_run:
        for f in audio_files:
            out_p = sahara_out / f"{f.stem}.json"
            is_valid = False
            if out_p.is_file():
                try:
                    c = json.loads(out_p.read_text(encoding="utf-8"))
                    is_valid = bool(not c.get("error") and c.get("transcript"))
                except Exception:
                    pass
            status = "SKIP (already exists)" if is_valid else "TRANSCRIBE"
            print(f"  [{status}] {f.name}  →  {out_p.name}")
        return []

    if not os.environ.get("SAHARA_API_KEY") and not _has_sahara_key():
        print(
            "\n⚠ SAHARA_API_KEY is not set. "
            "The client will fall back to Whisper large-v3.\n"
            "For intended Sahara runs, set SAHARA_API_KEY before running.\n"
        )

    sahara_out.mkdir(parents=True, exist_ok=True)
    results = []

    for i, audio_path in enumerate(audio_files, start=1):
        out_path = sahara_out / f"{audio_path.stem}.json"

        # Skip clip if valid transcript already exists on disk
        if out_path.is_file():
            try:
                cached = json.loads(out_path.read_text(encoding="utf-8"))
                if not cached.get("error") and cached.get("transcript") is not None:
                    snippet = (cached.get("transcript") or "")[:60].replace("\n", " ")
                    print(f'[{i}/{len(audio_files)}] {audio_path.name} ... SKIPPED (already exists: "{snippet}...")')
                    results.append(cached)
                    continue
            except Exception:
                pass

        print(f"[{i}/{len(audio_files)}] {audio_path.name} ...", end=" ", flush=True)

        result = transcribe_clip(audio_path)
        results.append(result)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            print(f"OK  (lang={result['language']}, conf={result['confidence']})")

        if i < len(audio_files) and delay_ms > 0:
            time.sleep(delay_ms / 1000)

    # Summary
    errors = [r for r in results if r["error"]]
    print(f"\nDone: {len(results)} clips, {len(errors)} errors.")
    if errors:
        print("Failed clips:")
        for r in errors:
            print(f"  {r['clip_id']}: {r['error']}")

    return results


def _has_sahara_key() -> bool:
    try:
        from app.config import settings  # noqa: PLC0415
        return bool(settings.sahara_api_key)
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Sahara v2.5 over a corpus tier.")
    p.add_argument(
        "--corpus",
        type=Path,
        default=_REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "audio",
        help="Directory containing audio files.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_REPO_ROOT / "bench" / "results" / "transcripts",
        help="Root directory for transcript output (transcripts go to <output-dir>/sahara/).",
    )
    p.add_argument("--delay-ms", type=int, default=200, help="ms between clips.")
    p.add_argument("--dry-run", action="store_true", help="Print plan without calling API.")
    p.add_argument("--clip-id", type=str, default=None, help="Run a single clip by ID.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_sahara(
        corpus_dir=args.corpus,
        output_dir=args.output_dir,
        delay_ms=args.delay_ms,
        dry_run=args.dry_run,
        clip_id=args.clip_id,
    )
