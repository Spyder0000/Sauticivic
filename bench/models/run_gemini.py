"""Run Gemini 3.5 Transcribe over a corpus tier and emit transcripts.

**Compute environment:** This script is designed to run on Google Colab or
cloud/local with the google-genai SDK. Gemini 3.5 Transcribe is a cloud API.
See ARCHITECTURE.md § Compute Environment.

Output
------
Writes one JSON file per audio clip to --output-dir:
    <output-dir>/gemini/<clip_id>.json
    {
        "clip_id": "...",
        "audio_file": "...",
        "transcript": "...",
        "language": "...",     # detected language or None
        "confidence": null,
        "backend": "gemini",
        "model": "gemini-3.5-transcribe",
        "error": null          # or error message if transcription failed
    }

The schema matches run_sahara.py / run_whisper.py / run_deepgram.py so the
metric scripts (wer.py, run_full_benchmark.py) read all four models identically.

Usage:
    # Set env var first:
    export GEMINI_API_KEY=your_key_here

    python3 bench/models/run_gemini.py \\
        --corpus bench/corpus/tier_a_recorded/audio \\
        --output-dir bench/results/transcripts \\
        [--model gemini-3.5-transcribe]  # default
        [--dry-run]                      # print plan without making API calls
        [--delay-ms 200]                 # ms between clips (rate limiting)
        [--clip bench/corpus/tier_a_recorded/audio/synth_001.wav]  # single clip by path
        [--clip-id synth_001]            # single clip by ID

After running, commit bench/results/transcripts/gemini/ back to the repo.
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
# Repo path setup (works both locally and on Colab after repo clone)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}


# ---------------------------------------------------------------------------
# Corpus discovery
# ---------------------------------------------------------------------------

def discover_audio_files(
    corpus_dir: Path,
    clip_id: str | None = None,
    clip_path: Path | None = None,
    clip_ids: set[str] | None = None,
) -> list[Path]:
    """Return all audio files in corpus_dir, or a single targeted clip."""
    if clip_path:
        p = Path(clip_path)
        if not p.is_file():
            # If relative path provided, try relative to repo root
            alt = _REPO_ROOT / clip_path
            if alt.is_file():
                return [alt]
            # Try within corpus_dir
            alt2 = corpus_dir / clip_path
            if alt2.is_file():
                return [alt2]
            return [p]
        return [p]

    if not corpus_dir.is_dir():
        return []

    files = sorted(
        p for p in corpus_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _AUDIO_EXTENSIONS
    )
    if clip_ids is not None:
        files = [f for f in files if f.stem in clip_ids or f.name in clip_ids]
    elif clip_id:
        # Match either exact stem or filename
        files = [f for f in files if f.stem == clip_id or f.name == clip_id]
    return files


def _should_reuse_existing(out_path: Path, force_overwrite: bool) -> bool:
    if force_overwrite or not out_path.is_file():
        return False
    try:
        cached = json.loads(out_path.read_text(encoding="utf-8"))
        return bool(not cached.get("error") and cached.get("transcript") is not None)
    except Exception:
        return False


def _resolve_tier_paths(
    tier: str,
    corpus_dir: Path | None,
    output_dir: Path | None,
) -> tuple[Path, Path]:
    if corpus_dir is None:
        corpus_dir = _REPO_ROOT / "bench" / "corpus" / (
            "tier_b_public" if tier == "b" else "tier_a_recorded/audio"
        )
    if output_dir is None:
        output_dir = _REPO_ROOT / "bench" / "results" / "transcripts"
        if tier == "b":
            output_dir /= "tier_b"
    return corpus_dir, output_dir


# ---------------------------------------------------------------------------
# Single-clip transcription
# ---------------------------------------------------------------------------

import re

def transcribe_clip(
    audio_path: Path,
    client,
    model_name: str = "gemini-3.5-transcribe",
    max_retries: int = 10,
) -> dict:
    """Transcribe one audio file via Gemini 3.5 Transcribe with retry/rate-limit handling.

    Uses verbatim mode to preserve Pidgin pragmatic particles and content words
    (e.g., 'abeg', 'abi', 'wetin', 'sef', 'sha') which smart mode would discard as fillers.
    """
    for attempt in range(1, max_retries + 1):
        try:
            audio_file = client.files.upload(file=str(audio_path))
            mime_type = getattr(audio_file, "mime_type", None) or "audio/wav"

            # Call interactions.create on Gemini 3.5 Transcribe
            interaction = client.interactions.create(
                model=model_name,
                input=[{
                    "type": "audio",
                    "uri": audio_file.uri,
                    "mime_type": mime_type,
                }],
                generation_config={
                    "transcription_config": {
                        # Do NOT lock to "en-US" only — our corpus is code-switched
                        # Pidgin/Yoruba/English. Omit language_codes to allow auto-detection.
                        "mode": {
                            "type": "verbatim",
                        }
                    }
                },
            )

            # Unpack transcript from interaction response
            transcript = ""
            if hasattr(interaction, "output_text") and interaction.output_text:
                transcript = interaction.output_text.strip()
            elif hasattr(interaction, "text") and interaction.text:
                transcript = interaction.text.strip()
            elif hasattr(interaction, "output") and interaction.output:
                transcript = str(interaction.output).strip()

            # Clean up temporary uploaded file if delete method exists
            try:
                if hasattr(client.files, "delete") and hasattr(audio_file, "name"):
                    client.files.delete(name=audio_file.name)
            except Exception:  # noqa: BLE001
                pass

            return {
                "clip_id": audio_path.stem,
                "audio_file": str(audio_path.name),
                "transcript": transcript,
                "language": getattr(interaction, "language", None),
                "confidence": None,
                "backend": "gemini",
                "model": model_name,
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001
            err_str = str(exc)
            if ("429" in err_str or "quota" in err_str.lower() or "too_many_requests" in err_str.lower()) and attempt < max_retries:
                # Extract wait time from error message or use fallback delay
                match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                if match:
                    wait_sec = float(match.group(1)) + 15.0
                else:
                    wait_sec = 30.0 * attempt
                print(f" [Rate limit (429): waiting {wait_sec:.1f}s before retry {attempt+1}/{max_retries}] ...", end=" ", flush=True)
                time.sleep(wait_sec)
                continue

            if attempt == max_retries:
                return {
                    "clip_id": audio_path.stem,
                    "audio_file": str(audio_path.name),
                    "transcript": "",
                    "language": None,
                    "confidence": None,
                    "backend": "gemini",
                    "model": model_name,
                    "error": str(exc),
                }
            time.sleep(5.0)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_gemini(
    corpus_dir: Path,
    output_dir: Path,
    model: str = "gemini-3.5-transcribe",
    delay_ms: int = 200,
    dry_run: bool = False,
    clip_id: str | None = None,
    clip_path: Path | None = None,
    clip_ids: set[str] | None = None,
) -> list[dict]:
    """Run Gemini 3.5 Transcribe over audio clips in corpus_dir.

    Args:
        corpus_dir: Directory containing audio files.
        output_dir: Root output dir. Transcripts go to output_dir/gemini/.
        model:      Gemini model name (default: gemini-3.5-transcribe).
        delay_ms:   Milliseconds to wait between clips (rate limiting).
        dry_run:    If True, print plan without making API calls.
        clip_id:    If set, only process this clip ID.
        clip_path:  If set, only process this audio file path.

    Returns:
        List of result dicts (one per clip).
    """
    gemini_out = output_dir if output_dir.name == "gemini" else output_dir / "gemini"
    audio_files = discover_audio_files(
        corpus_dir,
        clip_id=clip_id,
        clip_path=clip_path,
        clip_ids=clip_ids,
    )
    force_overwrite = clip_ids is not None

    if not audio_files:
        print(f"No audio files found in {corpus_dir}")
        return []

    print(f"Model:       Gemini ({model})")
    print(f"Corpus dir:  {corpus_dir}")
    print(f"Output dir:  {gemini_out}")
    print(f"Clips found: {len(audio_files)}")
    print(f"Delay:       {delay_ms}ms between clips")

    if dry_run:
        print("\n[DRY RUN] — validating configuration, no API calls will be made.\n")
        # Validate that google-genai SDK imports cleanly
        try:
            from google import genai  # noqa: F401, PLC0415
            print("✓ google-genai SDK is installed and importable.")
        except ImportError:
            print("⚠ google-genai SDK is not installed. Run `pip install google-genai`.")

        api_key = _resolve_api_key()
        if api_key:
            print("✓ GEMINI_API_KEY detected in environment/config.")
        else:
            print("ℹ GEMINI_API_KEY not yet set (required for live execution).")

        for f in audio_files:
            out_p = gemini_out / f"{f.stem}.json"
            is_valid = _should_reuse_existing(out_p, force_overwrite)
            status = "SKIP (already exists)" if is_valid else "TRANSCRIBE/OVERWRITE"
            print(f"  [{status}] {f.name}  →  {out_p.name}")
        return []

    # Live run requires API key
    api_key = _resolve_api_key()
    if not api_key:
        print(
            "\nERROR: GEMINI_API_KEY is not set.\n"
            "Set the key before running live transcription:\n"
            "    export GEMINI_API_KEY=your_key_here\n"
            "or set GEMINI_API_KEY in .env"
        )
        raise SystemExit(1)

    try:
        from google import genai  # noqa: PLC0415
    except ImportError as exc:
        print(
            "ERROR: google-genai is not installed.\n"
            "Install it via: pip install google-genai"
        )
        raise SystemExit(1) from exc

    client = genai.Client(api_key=api_key)

    gemini_out.mkdir(parents=True, exist_ok=True)
    results = []

    for i, audio_file in enumerate(audio_files, start=1):
        out_path = gemini_out / f"{audio_file.stem}.json"

        # Skip clip if valid transcript already exists on disk
        if _should_reuse_existing(out_path, force_overwrite):
            try:
                cached = json.loads(out_path.read_text(encoding="utf-8"))
                snippet = (cached.get("transcript") or "")[:60].replace("\n", " ")
                print(f'[{i}/{len(audio_files)}] {audio_file.name} ... SKIPPED (already exists: "{snippet}...")')
                results.append(cached)
                continue
            except Exception:
                pass

        print(f"[{i}/{len(audio_files)}] {audio_file.name} ...", end=" ", flush=True)

        result = transcribe_clip(audio_file, client, model_name=model)
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

    # Summary
    errors = [r for r in results if r["error"]]
    print(f"\nDone: {len(results)} clips, {len(errors)} errors.")
    if errors:
        print("Failed clips:")
        for r in errors:
            print(f"  {r['clip_id']}: {r['error']}")

    return results


def _resolve_api_key() -> str:
    """Resolve Gemini API key from environment variable, .env file, or app config."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv(_REPO_ROOT / ".env")
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if key:
            return key
    except Exception:
        pass
    env_file = _REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    try:
        from app.config import settings  # noqa: PLC0415
        return settings.gemini_api_key or ""
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Gemini 3.5 Transcribe over a corpus tier.")
    p.add_argument(
        "--corpus",
        type=Path,
        default=None,
        help="Directory containing audio files.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Root directory for transcript output (transcripts go to <output-dir>/gemini/).",
    )
    p.add_argument("--model", type=str, default="gemini-3.5-transcribe", help="Gemini model name.")
    p.add_argument("--delay-ms", type=int, default=200, help="ms between clips.")
    p.add_argument("--dry-run", action="store_true", help="Print plan without calling API.")
    p.add_argument("--tier", choices=("a", "b"), default="a", help="Corpus tier defaults to use.")
    target = p.add_mutually_exclusive_group()
    target.add_argument("--clip", type=Path, default=None, help="Run a single audio file path.")
    target.add_argument("--clip-id", type=str, default=None, help="Run a single clip by ID.")
    target.add_argument("--clips", type=str, default=None, help="Comma-separated clip IDs; selected outputs are overwritten.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    corpus_dir, output_dir = _resolve_tier_paths(args.tier, args.corpus, args.output_dir)
    clip_ids = {item.strip() for item in args.clips.split(",") if item.strip()} if args.clips else None
    run_gemini(
        corpus_dir=corpus_dir,
        output_dir=output_dir,
        model=args.model,
        delay_ms=args.delay_ms,
        dry_run=args.dry_run,
        clip_id=args.clip_id,
        clip_path=args.clip,
        clip_ids=clip_ids,
    )
