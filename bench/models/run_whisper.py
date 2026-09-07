"""Run Whisper large-v3 over a corpus tier and emit transcripts.

**Compute environment:** This script is designed to run on Google Colab or
cloud (GPU recommended for large-v3). Do NOT run this on the local dev machine.
See ARCHITECTURE.md § Compute Environment.

Output
------
Writes one JSON file per audio clip to --output-dir:
    <output-dir>/whisper/<clip_id>.json
    {
        "clip_id": "...",
        "audio_file": "...",
        "transcript": "...",
        "language": "...",
        "confidence": null,   # Whisper doesn't expose clip-level confidence
        "backend": "whisper",
        "model_size": "large-v3",
        "segments": [...],    # Whisper segment-level output, useful for WER analysis
        "error": null
    }

Usage (on Colab — GPU runtime recommended):
    !pip install openai-whisper
    !python3 bench/models/run_whisper.py \\
        --corpus bench/corpus/tier_a_recorded/audio \\
        --output-dir bench/results/transcripts \\
        [--model large-v3]   # default
        [--dry-run]
        [--clip-id synth_001]

After running, commit bench/results/transcripts/whisper/ back to the repo.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}


# ---------------------------------------------------------------------------
# Corpus discovery
# ---------------------------------------------------------------------------

def discover_audio_files(corpus_dir: Path, clip_id: str | None = None) -> list[Path]:
    """Return all audio files in corpus_dir (searching recursively), optionally filtered to one clip."""
    if not corpus_dir.is_dir():
        return []
    files = sorted(
        p for p in corpus_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _AUDIO_EXTENSIONS
    )
    if clip_id:
        files = [f for f in files if f.stem == clip_id or f.name == clip_id]
    return files


# ---------------------------------------------------------------------------
# Single-clip transcription
# ---------------------------------------------------------------------------

def transcribe_clip(audio_path: Path, model) -> dict:
    """Transcribe one audio file with Whisper. Returns a result dict."""
    try:
        result = model.transcribe(str(audio_path), task="transcribe")
        return {
            "clip_id": audio_path.stem,
            "audio_file": str(audio_path.name),
            "transcript": result["text"].strip(),
            "language": result.get("language"),
            "confidence": None,  # Whisper doesn't expose clip-level confidence
            "backend": "whisper",
            "model_size": model.dims.n_audio_ctx,  # stored for audit; actual name set at CLI level
            "segments": [
                {
                    "start": s["start"],
                    "end": s["end"],
                    "text": s["text"].strip(),
                    "avg_logprob": s.get("avg_logprob"),
                    "no_speech_prob": s.get("no_speech_prob"),
                }
                for s in result.get("segments", [])
            ],
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "clip_id": audio_path.stem,
            "audio_file": str(audio_path.name),
            "transcript": "",
            "language": None,
            "confidence": None,
            "backend": "whisper",
            "model_size": None,
            "segments": [],
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_whisper(
    corpus_dir: Path,
    output_dir: Path,
    model_size: str = "large-v3",
    delay_ms: int = 0,
    dry_run: bool = False,
    clip_id: str | None = None,
) -> list[dict]:
    """Run Whisper over all audio clips in corpus_dir.

    Args:
        corpus_dir:  Directory containing audio files.
        output_dir:  Root output dir. Transcripts go to output_dir/whisper/.
        model_size:  Whisper model size (default: large-v3).
        delay_ms:    ms to wait between clips (not usually needed for local inference).
        dry_run:     Print plan without loading model or running inference.
        clip_id:     If set, only process this one clip.

    Returns:
        List of result dicts.
    """
    whisper_out = output_dir / "whisper"
    audio_files = discover_audio_files(corpus_dir, clip_id)

    if not audio_files:
        print(f"No audio files found in {corpus_dir}")
        return []

    print(f"Model:       Whisper {model_size}")
    print(f"Corpus dir:  {corpus_dir}")
    print(f"Output dir:  {whisper_out}")
    print(f"Clips found: {len(audio_files)}")

    if dry_run:
        print("\n[DRY RUN] — model will not be loaded.\n")
        for f in audio_files:
            print(f"  would transcribe: {f.name}  →  {whisper_out / f.stem}.json")
        return []

    # Load model once — expensive, cache for the whole run
    try:
        import whisper  # type: ignore[import]
    except ImportError as exc:
        print(
            "ERROR: openai-whisper is not installed.\n"
            "On Colab: !pip install openai-whisper\n"
            "This script is designed to run on Colab/cloud, not locally."
        )
        raise SystemExit(1) from exc

    print(f"\nLoading Whisper {model_size} (this may take a minute on first run)...")
    model = whisper.load_model(model_size)
    print("Model loaded.\n")

    whisper_out.mkdir(parents=True, exist_ok=True)
    results = []

    for i, audio_path in enumerate(audio_files, start=1):
        out_path = whisper_out / f"{audio_path.stem}.json"
        print(f"[{i}/{len(audio_files)}] {audio_path.name} ...", end=" ", flush=True)

        result = transcribe_clip(audio_path, model)
        # Store model size as string in the output
        result["model_size"] = model_size
        results.append(result)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            snippet = result["transcript"][:60].replace("\n", " ")
            print(f'OK  (lang={result["language"]})  "{snippet}..."')

        if i < len(audio_files) and delay_ms > 0:
            time.sleep(delay_ms / 1000)

    errors = [r for r in results if r["error"]]
    print(f"\nDone: {len(results)} clips, {len(errors)} errors.")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Whisper large-v3 over a corpus tier.")
    p.add_argument(
        "--corpus",
        type=Path,
        default=_REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "audio",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_REPO_ROOT / "bench" / "results" / "transcripts",
        help="Root dir — transcripts go to <output-dir>/whisper/.",
    )
    p.add_argument("--model", type=str, default="large-v3", dest="model_size")
    p.add_argument("--delay-ms", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--clip-id", type=str, default=None)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_whisper(
        corpus_dir=args.corpus,
        output_dir=args.output_dir,
        model_size=args.model_size,
        delay_ms=args.delay_ms,
        dry_run=args.dry_run,
        clip_id=args.clip_id,
    )
