"""Run Deepgram Nova-3 over a corpus tier and emit transcripts.

**Compute environment:** This script is designed to run on Google Colab or
cloud, NOT on the local dev machine. Deepgram is a cloud API.
See ARCHITECTURE.md § Compute Environment.

Output
------
Writes one JSON file per audio clip to --output-dir:
    <output-dir>/deepgram/<clip_id>.json
    {
        "clip_id": "...",
        "audio_file": "...",
        "transcript": "...",
        "language": "...",     # detected language (detect_language=True)
        "confidence": 0.0–1.0,
        "backend": "deepgram",
        "model": "nova-3",
        "error": null           # or error message if transcription failed
    }

The schema matches run_sahara.py / run_whisper.py so the metric scripts read
all three models identically.

Usage (on Colab / cloud):
    !pip install deepgram-sdk==3.8.1
    export DEEPGRAM_API_KEY=your_key_here

    python3 bench/models/run_deepgram.py \\
        --corpus bench/corpus/tier_a_recorded/audio \\
        --output-dir bench/results/transcripts \\
        [--model nova-3]      # default
        [--dry-run]           # print plan without making API calls
        [--delay-ms 200]      # ms between clips (rate limiting)
        [--clip-id synth_001] # run a single clip only

After running, commit bench/results/transcripts/deepgram/ back to the repo.
Metric scripts (wer.py, run_full_benchmark.py) then run locally.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo path setup (works both locally and on Colab after repo clone).
# Only needed for the optional config-based API-key fallback below.
# ---------------------------------------------------------------------------
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

def transcribe_clip(audio_path: Path, transcriber, options, model_name: str) -> dict:
    """Transcribe one audio file via Deepgram. Returns a result dict.

    Args:
        audio_path:  Path to the audio file.
        transcriber: A Deepgram REST transcription handle (``.transcribe_file``).
        options:     A PrerecordedOptions instance (model, smart_format, ...).
        model_name:  Model name, stored in the output for audit.
    """
    try:
        payload = {"buffer": audio_path.read_bytes()}
        response = transcriber.transcribe_file(payload, options)

        # Deepgram v3 response: results.channels[0].alternatives[0]
        channel = response.results.channels[0]
        alt = channel.alternatives[0]
        return {
            "clip_id": audio_path.stem,
            "audio_file": str(audio_path.name),
            "transcript": (alt.transcript or "").strip(),
            "language": getattr(channel, "detected_language", None),
            "confidence": getattr(alt, "confidence", None),
            "backend": "deepgram",
            "model": model_name,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "clip_id": audio_path.stem,
            "audio_file": str(audio_path.name),
            "transcript": "",
            "language": None,
            "confidence": None,
            "backend": "deepgram",
            "model": model_name,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_deepgram(
    corpus_dir: Path,
    output_dir: Path,
    model: str = "nova-3",
    delay_ms: int = 200,
    dry_run: bool = False,
    clip_id: str | None = None,
) -> list[dict]:
    """Run Deepgram over all audio clips in corpus_dir.

    Args:
        corpus_dir: Directory containing audio files.
        output_dir: Root output dir. Transcripts go to output_dir/deepgram/.
        model:      Deepgram model name (default: nova-3).
        delay_ms:   Milliseconds to wait between clips (rate limiting).
        dry_run:    If True, print plan without making API calls.
        clip_id:    If set, only process this one clip.

    Returns:
        List of result dicts (one per clip).
    """
    deepgram_out = output_dir / "deepgram"
    audio_files = discover_audio_files(corpus_dir, clip_id)

    if not audio_files:
        print(f"No audio files found in {corpus_dir}")
        return []

    print(f"Model:       Deepgram {model}")
    print(f"Corpus dir:  {corpus_dir}")
    print(f"Output dir:  {deepgram_out}")
    print(f"Clips found: {len(audio_files)}")
    print(f"Delay:       {delay_ms}ms between clips")

    if dry_run:
        print("\n[DRY RUN] — no API calls will be made.\n")
        for f in audio_files:
            print(f"  would transcribe: {f.name}  →  {deepgram_out / f.stem}.json")
        return []

    # Unlike Sahara (which falls back to Whisper), Deepgram *requires* a key.
    api_key = _resolve_api_key()
    if not api_key:
        print(
            "\nERROR: DEEPGRAM_API_KEY is not set (and no deepgram_api_key in config).\n"
            "Deepgram is a cloud API with no offline fallback — set the key before running:\n"
            "    export DEEPGRAM_API_KEY=your_key_here\n"
        )
        raise SystemExit(1)

    # Lazy import — keeps the module importable locally (dry-run, tests) without
    # the SDK installed. On Colab: !pip install deepgram-sdk==3.8.1
    try:
        from deepgram import DeepgramClient, PrerecordedOptions  # type: ignore[import]
    except ImportError as exc:
        print(
            "ERROR: deepgram-sdk is not installed.\n"
            "On Colab: !pip install deepgram-sdk==3.8.1\n"
            "This script is designed to run on Colab/cloud, not locally."
        )
        raise SystemExit(1) from exc

    client = DeepgramClient(api_key)
    # The prerecorded-file namespace moved from `listen.prerecorded` to
    # `listen.rest` across v3 SDK builds — support both.
    listen = client.listen
    namespace = getattr(listen, "rest", None) or getattr(listen, "prerecorded", None)
    if namespace is None:
        print("ERROR: could not locate the Deepgram REST transcription namespace.")
        raise SystemExit(1)
    transcriber = namespace.v("1")
    options = PrerecordedOptions(model=model, smart_format=True, detect_language=True)

    deepgram_out.mkdir(parents=True, exist_ok=True)
    results = []

    for i, audio_path in enumerate(audio_files, start=1):
        out_path = deepgram_out / f"{audio_path.stem}.json"

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

        result = transcribe_clip(audio_path, transcriber, options, model)
        results.append(result)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            snippet = result["transcript"][:60].replace("\n", " ")
            print(f'OK  (lang={result["language"]}, conf={result["confidence"]})  "{snippet}..."')

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


def _resolve_api_key() -> str:
    """Resolve the Deepgram API key from env, falling back to .env file or app config."""
    key = os.environ.get("DEEPGRAM_API_KEY")
    if key:
        return key
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv(_REPO_ROOT / ".env")
        key = os.environ.get("DEEPGRAM_API_KEY")
        if key:
            return key
    except Exception:
        pass
    env_file = _REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DEEPGRAM_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    try:
        from app.config import settings  # noqa: PLC0415
        return settings.deepgram_api_key or ""
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Deepgram Nova-3 over a corpus tier.")
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
        help="Root directory for transcript output (transcripts go to <output-dir>/deepgram/).",
    )
    p.add_argument("--model", type=str, default="nova-3", help="Deepgram model name.")
    p.add_argument("--delay-ms", type=int, default=200, help="ms between clips.")
    p.add_argument("--dry-run", action="store_true", help="Print plan without calling API.")
    p.add_argument("--clip-id", type=str, default=None, help="Run a single clip by ID.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_deepgram(
        corpus_dir=args.corpus,
        output_dir=args.output_dir,
        model=args.model,
        delay_ms=args.delay_ms,
        dry_run=args.dry_run,
        clip_id=args.clip_id,
    )
