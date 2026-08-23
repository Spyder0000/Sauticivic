"""Convert raw recordings to the ASR input format, then A/B-validate the result.

**Compute environment:** This script is designed to run on Google Colab or
cloud, NOT on the local dev machine (it needs ffmpeg). See ARCHITECTURE.md
§ Compute Environment.

Why this exists (plan §4.4)
---------------------------
A preprocessing bug (wrong sample rate, silent channel mixdown, clipping from a
bad gain stage) looks *exactly* like a weak ASR model on the benchmark. This
script catches that class of bug before it gets blamed on a model, by doing an
A/B check: the file is CONVERTED with one tool (ffmpeg) and then re-decoded and
measured with an INDEPENDENT tool (Python's stdlib ``wave``, plus ``soundfile``
if installed). If the two disagree, or the output drifts from the target spec,
it is flagged.

Target spec: 16 kHz, mono, 16-bit signed PCM WAV — the standard ASR input.

Checks per clip
---------------
  - sample_rate == 16000, channels == 1, sample_width == 2 bytes
  - duration drift vs. source (via ffprobe) within tolerance
  - not silent (RMS above an epsilon — catches dead-channel mixdowns)
  - not clipped (fraction of full-scale samples below threshold — catches gain bugs)
  - decoders agree (wave vs. soundfile readback match — the core A/B)

Usage (on Colab / cloud):
    !apt-get -qq install ffmpeg && pip install soundfile
    python3 bench/audio_preprocessing/convert_and_validate.py \\
        --input-dir bench/corpus/tier_a_recorded/raw \\
        --output-dir bench/corpus/tier_a_recorded/audio \\
        [--target-sr 16000]
        [--dry-run]
        [--clip-id synth_001]

Writes a committed JSON report (preprocessing_ab_report.json) to --output-dir.
The converted WAVs themselves are gitignored (audio is not committed).
"""
from __future__ import annotations

import argparse
import array
import json
import math
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm"}

# --- Target ASR input spec ---
TARGET_SR = 16000
TARGET_CHANNELS = 1
TARGET_SAMPLE_WIDTH_BYTES = 2  # 16-bit signed PCM

# --- Validation tolerances ---
DURATION_TOLERANCE_S = 0.05     # 50 ms drift between source and converted output
SILENCE_RMS_THRESHOLD = 1e-4    # normalized RMS below this ≈ silence (~ -80 dBFS)
CLIP_FRACTION_THRESHOLD = 0.01  # >1% of samples at full-scale ⇒ likely a gain bug


# ---------------------------------------------------------------------------
# Discovery + ffmpeg/ffprobe helpers
# ---------------------------------------------------------------------------

def discover_audio_files(input_dir: Path, clip_id: str | None = None) -> list[Path]:
    """Return raw audio files in input_dir, optionally filtered to one clip."""
    if not input_dir.is_dir():
        return []
    files = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _AUDIO_EXTENSIONS
    )
    if clip_id:
        files = [f for f in files if f.stem == clip_id]
    return files


def _tool_available(tool: str) -> bool:
    try:
        subprocess.run([tool, "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _probe_duration(path: Path) -> float | None:
    """Return the media duration in seconds via ffprobe or ffmpeg fallback, or None on failure."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        pass

    try:
        out = subprocess.run(
            ["ffmpeg", "-i", str(path)],
            capture_output=True, text=True,
        )
        import re
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out.stderr)
        if m:
            h, mins, s = m.groups()
            return int(h) * 3600 + int(mins) * 60 + float(s)
    except Exception:
        pass

    return None


def _convert(src: Path, dst: Path, target_sr: int) -> None:
    """Convert src → dst as target_sr mono 16-bit PCM WAV using ffmpeg."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src),
            "-ar", str(target_sr),
            "-ac", str(TARGET_CHANNELS),
            "-c:a", "pcm_s16le",
            str(dst),
        ],
        capture_output=True, text=True, check=True,
    )


# ---------------------------------------------------------------------------
# Independent readback (the A/B "reference tool" side)
# ---------------------------------------------------------------------------

def _read_wav_stdlib(path: Path) -> dict:
    """Re-decode a WAV with the stdlib ``wave`` module (independent of ffmpeg).

    Returns sample rate, channels, sample width, duration, and — when the file
    is 16-bit — normalized RMS and clipping fraction.
    """
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    duration = (n_frames / sr) if sr else None
    rms = clip_fraction = None
    if width == 2 and raw:
        samples = array.array("h")
        samples.frombytes(raw)
        n = len(samples)
        if n:
            sq = 0.0
            clipped = 0
            for s in samples:
                sq += (s / 32768.0) ** 2
                if s >= 32767 or s <= -32768:
                    clipped += 1
            rms = math.sqrt(sq / n)
            clip_fraction = clipped / n

    return {
        "sample_rate": sr,
        "channels": channels,
        "sample_width_bytes": width,
        "duration_s": duration,
        "rms": rms,
        "clip_fraction": clip_fraction,
    }


def _read_wav_soundfile(path: Path) -> dict | None:
    """Second-opinion readback via soundfile, if it (and numpy) are installed.

    Returns None when soundfile is unavailable — the stdlib readback still
    provides an independent decoder, so the A/B check degrades but doesn't break.
    """
    try:
        import soundfile as sf  # type: ignore[import]
    except ImportError:
        return None
    try:
        data, sr = sf.read(str(path))
        n = data.shape[0]
        channels = 1 if data.ndim == 1 else data.shape[1]
        return {
            "sample_rate": int(sr),
            "channels": int(channels),
            "duration_s": (n / sr) if sr else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Per-clip convert + validate
# ---------------------------------------------------------------------------

def validate_conversion(src: Path, dst: Path, target_sr: int) -> dict:
    """Convert one clip and A/B-validate the output. Returns a result dict."""
    target_spec = {
        "sample_rate": target_sr,
        "channels": TARGET_CHANNELS,
        "sample_width_bytes": TARGET_SAMPLE_WIDTH_BYTES,
        "format": "wav_pcm_s16le",
    }
    try:
        source_duration = _probe_duration(src)
        _convert(src, dst, target_sr)

        measured = _read_wav_stdlib(dst)
        sf_read = _read_wav_soundfile(dst)

        warnings: list[str] = []

        sample_rate_ok = measured["sample_rate"] == target_sr
        channels_ok = measured["channels"] == TARGET_CHANNELS
        width_ok = measured["sample_width_bytes"] == TARGET_SAMPLE_WIDTH_BYTES

        if source_duration is not None and measured["duration_s"] is not None:
            duration_ok = abs(measured["duration_s"] - source_duration) <= DURATION_TOLERANCE_S
            if not duration_ok:
                warnings.append(
                    f"duration drift {measured['duration_s']:.3f}s vs source "
                    f"{source_duration:.3f}s (> {DURATION_TOLERANCE_S}s)"
                )
        else:
            duration_ok = None  # source duration unknown (ffprobe unavailable)

        not_silent = measured["rms"] is not None and measured["rms"] > SILENCE_RMS_THRESHOLD
        if measured["rms"] is not None and not not_silent:
            warnings.append(f"near-silent output (rms={measured['rms']:.2e})")

        not_clipped = measured["clip_fraction"] is None or measured["clip_fraction"] <= CLIP_FRACTION_THRESHOLD
        if measured["clip_fraction"] is not None and not not_clipped:
            warnings.append(f"clipping: {measured['clip_fraction']:.1%} of samples at full-scale")

        # Core A/B: do the two independent decoders agree on sr / channels / duration?
        decoders_agree: bool | None = None
        if sf_read and "error" not in sf_read:
            sr_match = sf_read["sample_rate"] == measured["sample_rate"]
            ch_match = sf_read["channels"] == measured["channels"]
            dur_match = (
                sf_read["duration_s"] is not None
                and measured["duration_s"] is not None
                and abs(sf_read["duration_s"] - measured["duration_s"]) <= DURATION_TOLERANCE_S
            )
            decoders_agree = bool(sr_match and ch_match and dur_match)
            if not decoders_agree:
                warnings.append(
                    "decoder disagreement (wave vs soundfile): "
                    f"wave={measured['sample_rate']}Hz/{measured['channels']}ch "
                    f"soundfile={sf_read['sample_rate']}Hz/{sf_read['channels']}ch"
                )
        elif sf_read and "error" in sf_read:
            warnings.append(f"soundfile readback failed: {sf_read['error']}")

        checks = {
            "sample_rate_ok": sample_rate_ok,
            "channels_ok": channels_ok,
            "sample_width_ok": width_ok,
            "duration_ok": duration_ok,
            "not_silent": not_silent,
            "not_clipped": not_clipped,
            "decoders_agree": decoders_agree,
        }

        # ok = every critical check that produced a boolean is True.
        # (Clipping is a warning, not a hard fail — some clips legitimately clip.)
        critical = [
            sample_rate_ok, channels_ok, width_ok, not_silent,
            duration_ok if duration_ok is not None else True,
            decoders_agree if decoders_agree is not None else True,
        ]
        ok = all(critical)

        return {
            "clip_id": src.stem,
            "source_file": src.name,
            "output_file": dst.name,
            "target_spec": target_spec,
            "source_duration_s": source_duration,
            "measured": measured,
            "soundfile_readback": sf_read,
            "checks": checks,
            "warnings": warnings,
            "ok": ok,
            "error": None,
        }
    except subprocess.CalledProcessError as exc:
        return _error_result(src, dst, target_spec, f"ffmpeg failed: {exc.stderr or exc}")
    except Exception as exc:  # noqa: BLE001
        return _error_result(src, dst, target_spec, str(exc))


def _error_result(src: Path, dst: Path, target_spec: dict, msg: str) -> dict:
    return {
        "clip_id": src.stem,
        "source_file": src.name,
        "output_file": dst.name,
        "target_spec": target_spec,
        "source_duration_s": None,
        "measured": None,
        "soundfile_readback": None,
        "checks": {},
        "warnings": [],
        "ok": False,
        "error": msg,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def convert_and_validate(
    input_dir: Path,
    output_dir: Path,
    target_sr: int = TARGET_SR,
    dry_run: bool = False,
    clip_id: str | None = None,
) -> list[dict]:
    """Convert + A/B-validate every raw clip in input_dir. Returns result dicts."""
    audio_files = discover_audio_files(input_dir, clip_id)

    if not audio_files:
        print(f"No audio files found in {input_dir}")
        return []

    print(f"Input dir:   {input_dir}")
    print(f"Output dir:  {output_dir}")
    print(f"Target:      {target_sr} Hz, {TARGET_CHANNELS}ch, 16-bit PCM WAV")
    print(f"Clips found: {len(audio_files)}")

    if dry_run:
        print("\n[DRY RUN] — no conversion will be performed.\n")
        for f in audio_files:
            print(f"  would convert: {f.name}  →  {output_dir / (f.stem + '.wav')}")
        return []

    if not _tool_available("ffmpeg"):
        print(
            "\nERROR: ffmpeg is not installed.\n"
            "On Colab: !apt-get -qq install ffmpeg\n"
            "This script is designed to run on Colab/cloud, not locally."
        )
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for i, src in enumerate(audio_files, start=1):
        dst = output_dir / f"{src.stem}.wav"
        print(f"[{i}/{len(audio_files)}] {src.name} ...", end=" ", flush=True)

        result = validate_conversion(src, dst, target_sr)
        results.append(result)

        if result["error"]:
            print(f"ERROR: {result['error']}")
        elif result["ok"] and not result["warnings"]:
            print("OK")
        elif result["ok"]:
            print(f"OK (warnings: {'; '.join(result['warnings'])})")
        else:
            failed = [k for k, v in result["checks"].items() if v is False]
            print(f"DIVERGENT — failed: {', '.join(failed)}")

    # --- Summary + committed report ---
    ok_count = sum(1 for r in results if r["ok"])
    divergent = [r for r in results if not r["ok"]]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_spec": {
            "sample_rate": target_sr,
            "channels": TARGET_CHANNELS,
            "sample_width_bytes": TARGET_SAMPLE_WIDTH_BYTES,
            "format": "wav_pcm_s16le",
        },
        "method": "convert(ffmpeg) + independent readback(wave + soundfile) A/B check",
        "total": len(results),
        "ok_count": ok_count,
        "divergent_count": len(divergent),
        "results": results,
    }
    report_path = output_dir / "preprocessing_ab_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nDone: {len(results)} clips, {ok_count} OK, {len(divergent)} divergent.")
    if divergent:
        print("Divergent clips (investigate as preprocessing bugs, not model weakness):")
        for r in divergent:
            detail = r["error"] or "; ".join(r["warnings"]) or "failed checks"
            print(f"  {r['clip_id']}: {detail}")
    print(f"Report written to: {report_path}")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert raw recordings to ASR format and A/B-validate them."
    )
    p.add_argument(
        "--input-dir",
        type=Path,
        default=_REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "raw",
        help="Directory containing raw recordings to convert.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "audio",
        help="Directory for converted WAVs + the A/B report JSON.",
    )
    p.add_argument("--target-sr", type=int, default=TARGET_SR, help="Target sample rate (Hz).")
    p.add_argument("--dry-run", action="store_true", help="Print plan without converting.")
    p.add_argument("--clip-id", type=str, default=None, help="Process a single clip by ID.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    convert_and_validate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        target_sr=args.target_sr,
        dry_run=args.dry_run,
        clip_id=args.clip_id,
    )
