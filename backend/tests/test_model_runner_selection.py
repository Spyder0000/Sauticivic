from pathlib import Path

import pytest

from bench.models import run_deepgram, run_gemini, run_sahara


@pytest.mark.parametrize("runner", [run_sahara, run_deepgram, run_gemini])
def test_discover_audio_files_filters_multiple_clip_ids(tmp_path, runner):
    for clip_id in ("afriswitch_pcm_001", "afriswitch_pcm_002", "afriswitch_yor_001"):
        (tmp_path / f"{clip_id}.wav").touch()

    selected = runner.discover_audio_files(
        tmp_path,
        clip_ids={"afriswitch_pcm_001", "afriswitch_pcm_002"},
    )

    assert [path.stem for path in selected] == [
        "afriswitch_pcm_001",
        "afriswitch_pcm_002",
    ]


@pytest.mark.parametrize("runner", [run_sahara, run_deepgram, run_gemini])
def test_explicit_clip_list_forces_overwrite_of_existing_transcripts(tmp_path, runner):
    existing = tmp_path / "afriswitch_pcm_001.json"
    existing.write_text('{"transcript": "stale", "error": null}', encoding="utf-8")

    assert not runner._should_reuse_existing(existing, force_overwrite=True)
    assert runner._should_reuse_existing(existing, force_overwrite=False)


@pytest.mark.parametrize("runner", [run_sahara, run_deepgram, run_gemini])
def test_tier_b_defaults_point_to_public_audio_and_tier_b_outputs(runner):
    corpus, output = runner._resolve_tier_paths("b", None, None)

    assert corpus == runner._REPO_ROOT / "bench" / "corpus" / "tier_b_public"
    assert output == runner._REPO_ROOT / "bench" / "results" / "transcripts" / "tier_b"
