import json

from bench.metrics.run_tier_a_multispeaker_validation import (
    aggregate_polarity,
    adjudicate_target,
    count_expected_targets,
    load_cached_transcript,
)


def test_literal_don_is_preserved():
    result = adjudicate_target(
        "e don spoil plenty tyre", "e don spoil plenty tyre", "don"
    )
    assert result["outcome"] == "preserved"


def test_dont_and_doesnt_are_inversions():
    assert adjudicate_target("e don spoil", "it don't spoil", "don")["outcome"] == "inverted"
    assert adjudicate_target("e don spoil", "it doesn't spoil", "don")["outcome"] == "inverted"


def test_affirmative_and_negative_paraphrases():
    assert adjudicate_target("e don spoil", "it has damaged", "don")["outcome"] == "preserved"
    assert adjudicate_target("e don spoil", "it has not damaged", "don")["outcome"] == "inverted"


def test_deleted_and_corrupted_targets_are_distinct():
    assert adjudicate_target("e don spoil", "there is a pothole", "don")["outcome"] == "deleted"
    assert adjudicate_target("e don spoil", "it down sports plenty trial", "don")["outcome"] == "ambiguous"


def test_prompt_002_has_two_targets_and_mixed_outcome():
    reference = "Water don burst for our street since morning, everywhere don flood."
    targets = [
        adjudicate_target("Water don burst", "Water has burst", "don"),
        adjudicate_target("everywhere don flood", "everywhere don't flood", "don"),
    ]
    assert len(targets) == 2
    assert [x["outcome"] for x in targets] == ["preserved", "inverted"]


def test_control_has_no_expected_targets():
    corpus = [{"contains_don_marker": False, "don_token_count": 0}]
    assert count_expected_targets(corpus) == 0


def test_aggregate_uses_exact_denominators():
    rows = [
        {"outcome": "preserved", "clip_id": "a"},
        {"outcome": "inverted", "clip_id": "b"},
        {"outcome": "deleted", "clip_id": "c"},
        {"outcome": "ambiguous", "clip_id": "d"},
        {"outcome": "inverted", "clip_id": "b"},
    ]
    result = aggregate_polarity(rows, expected_targets=5, target_clip_ids={"a", "b", "c", "d"})
    assert result["token_counts"] == {
        "preserved": 1,
        "inverted": 2,
        "deleted": 1,
        "ambiguous": 1,
    }
    assert result["token_inversion_rate"] == 2 / 5
    assert result["utterance_inversion_count"] == 1
    assert result["utterance_denominator"] == 4


def test_cached_transcript_reuse_and_missing_transcript(tmp_path):
    path = tmp_path / "clip.json"
    path.write_text(json.dumps({"clip_id": "x", "transcript": "cached", "error": None}), encoding="utf-8")
    assert load_cached_transcript(path)["transcript"] == "cached"

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"clip_id": "x", "transcript": "", "error": "timeout"}), encoding="utf-8")
    assert load_cached_transcript(bad) is None


def test_per_speaker_aggregation():
    speaker_rows = [
        {"outcome": "preserved", "clip_id": "spk3_001", "speaker_id": "SPK-03"},
        {"outcome": "inverted", "clip_id": "spk3_002", "speaker_id": "SPK-03"},
    ]
    res = aggregate_polarity(speaker_rows, expected_targets=7, target_clip_ids={"spk3_001", "spk3_002"})
    assert res["token_counts"]["preserved"] == 1
    assert res["token_counts"]["inverted"] == 1
    assert res["expected_token_denominator"] == 7
    assert res["token_inversion_rate"] == 1 / 7
    assert res["utterance_inversion_count"] == 1
    assert res["utterance_denominator"] == 2


def test_raw_output_immutability_during_adjudication():
    raw_hyp = "  It Don't Spoil Plenty Tyre.  "
    orig_copy = str(raw_hyp)
    row = adjudicate_target("e don spoil", raw_hyp, "don")
    # Verify raw hypothesis string is unchanged
    assert raw_hyp == orig_copy
    assert row["outcome"] == "inverted"
    assert "it don't spoil" in row["evidence_span"]

