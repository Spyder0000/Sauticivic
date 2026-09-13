import json

from bench.corpus.tier_b_public.ingest_tier_b import (
    _can_write_upstream,
    _has_complete_existing_clips,
    _upstream_id,
    save_clip,
)


def test_existing_afriswitch_clips_with_empty_transcript_require_refresh(tmp_path):
    for index in range(1, 11):
        clip_id = f"afriswitch_pcm_{index:03d}"
        (tmp_path / f"{clip_id}.wav").touch()
        (tmp_path / f"{clip_id}.json").write_text(
            json.dumps({"transcript": "" if index == 1 else "valid reference"}),
            encoding="utf-8",
        )

    assert not _has_complete_existing_clips(tmp_path, 10)


def test_existing_afriswitch_clips_with_transcripts_can_be_reused(tmp_path):
    for index in range(1, 11):
        clip_id = f"afriswitch_pcm_{index:03d}"
        (tmp_path / f"{clip_id}.wav").touch()
        (tmp_path / f"{clip_id}.json").write_text(
            json.dumps({"transcript": "valid reference", "upstream_id": clip_id}),
            encoding="utf-8",
        )

    assert _has_complete_existing_clips(tmp_path, 10)


def test_upstream_id_uses_stable_source_fields_before_index_fallback():
    assert _upstream_id({"id": "row-id", "filename": "audio.wav"}, 4) == "row-id"
    assert _upstream_id({"audio_id": "audio-id", "filename": "audio.wav"}, 4) == "audio-id"
    assert _upstream_id({"filename": "audio.wav"}, 4) == "audio.wav"
    assert _upstream_id({}, 4) == "index_4"


def test_mismatched_upstream_id_warns_and_prevents_overwrite(tmp_path, capsys):
    sidecar = tmp_path / "afriswitch_pcm_001.json"
    sidecar.write_text(json.dumps({"upstream_id": "old.wav"}), encoding="utf-8")

    assert not _can_write_upstream(sidecar, "new.wav")
    assert "WARNING" in capsys.readouterr().out
    assert "old.wav" in sidecar.read_text(encoding="utf-8")


def test_save_clip_persists_upstream_id(tmp_path):
    import numpy as np

    output = tmp_path / "afriswitch_pcm_001.wav"
    save_clip(
        np.zeros(16000, dtype=np.float32),
        16000,
        output,
        "reference",
        {"source": "afriswitch", "upstream_id": "source.wav"},
    )

    sidecar = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    assert sidecar["upstream_id"] == "source.wav"
