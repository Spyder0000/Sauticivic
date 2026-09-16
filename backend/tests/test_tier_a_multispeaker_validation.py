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


def test_non_latin_hallucinations_are_ambiguous():
    gurmukhi = "੧ ੧ ੧ ੧ ੧ ੧ ੧ ੧"
    bengali = "রে রে রে রে রে রে"
    malayalam = "തതതതതതതത"
    assert adjudicate_target("e don dark", gurmukhi, "don")["outcome"] == "ambiguous"
    assert adjudicate_target("e don collect", bengali, "don")["outcome"] == "ambiguous"
    assert adjudicate_target("e don chase", malayalam, "don")["outcome"] == "ambiguous"


def test_synth_002_both_targets_handled_separately():
    # SPK-03: done buzz / done flood
    t1_spk3 = adjudicate_target("Water don burst", "Water done buzz for our streets since morning, everywhere done flood.", "don", prompt_number=2, target_index=1)
    t2_spk3 = adjudicate_target("everywhere don flood", "Water done buzz for our streets since morning, everywhere done flood.", "don", prompt_number=2, target_index=2)
    assert t1_spk3["outcome"] == "ambiguous"
    assert t2_spk3["outcome"] == "preserved"

    # SPK-04: don't boast / don't float
    t1_spk4 = adjudicate_target("Water don burst", "Potsah don't boast for a street since morning. Everywhere don't float.", "don", prompt_number=2, target_index=1)
    t2_spk4 = adjudicate_target("everywhere don flood", "Potsah don't boast for a street since morning. Everywhere don't float.", "don", prompt_number=2, target_index=2)
    assert t1_spk4["outcome"] == "inverted"
    assert t2_spk4["outcome"] == "inverted"


def test_msv_four_model_results_json():
    from pathlib import Path
    results_path = Path("bench/results/tier_a_multispeaker_validation_results.json")
    assert results_path.is_file()
    data = json.loads(results_path.read_text(encoding="utf-8"))

    models = data["models"]
    for m in ("sahara", "gemini", "deepgram", "whisper"):
        assert m in models
        assert models[m]["status"] == "ok"
        assert models[m]["successful_clips"] == 30
        assert models[m]["polarity"]["expected_token_denominator"] == 21
        assert models[m]["polarity"]["utterance_denominator"] == 18

    # Sahara: 0/21 inversions, 0/18 affected utterances
    assert models["sahara"]["polarity"]["token_counts"]["inverted"] == 0
    assert models["sahara"]["polarity"]["token_counts"]["preserved"] == 21
    assert models["sahara"]["polarity"]["utterance_inversion_count"] == 0

    # Gemini: 10/21 inversions, 9/18 affected utterances
    assert models["gemini"]["polarity"]["token_counts"]["inverted"] == 10
    assert models["gemini"]["polarity"]["token_counts"]["preserved"] == 8
    assert models["gemini"]["polarity"]["token_counts"]["ambiguous"] == 3
    assert models["gemini"]["polarity"]["utterance_inversion_count"] == 9

    # Deepgram: 10/21 inversions, 1 preserved, 1 deleted, 9 ambiguous, 9/18 affected utterances
    assert models["deepgram"]["polarity"]["token_counts"]["inverted"] == 10
    assert models["deepgram"]["polarity"]["token_counts"]["preserved"] == 1
    assert models["deepgram"]["polarity"]["token_counts"]["deleted"] == 1
    assert models["deepgram"]["polarity"]["token_counts"]["ambiguous"] == 9
    assert models["deepgram"]["polarity"]["utterance_inversion_count"] == 9
    assert models["deepgram"]["polarity"]["utterance_denominator"] == 18

    # Whisper: 11/21 inversions, 10/18 affected utterances
    assert models["whisper"]["polarity"]["token_counts"]["inverted"] == 11
    assert models["whisper"]["polarity"]["utterance_inversion_count"] == 10
    assert models["whisper"]["polarity"]["token_counts"]["preserved"] == 1
    assert models["whisper"]["polarity"]["token_counts"]["ambiguous"] == 9


def test_msv_model_invariants_sum_and_unique_keys():
    from pathlib import Path
    results_path = Path("bench/results/tier_a_multispeaker_validation_results.json")
    assert results_path.is_file()
    data = json.loads(results_path.read_text(encoding="utf-8"))

    for model_name in ("sahara", "gemini", "deepgram", "whisper"):
        model_data = data["models"][model_name]
        tc = model_data["polarity"]["token_counts"]

        # Invariant 1: inverted + preserved + deleted + ambiguous = 21
        total_tokens = tc["inverted"] + tc["preserved"] + tc["deleted"] + tc["ambiguous"]
        assert total_tokens == 21, f"{model_name} total tokens {total_tokens} != 21"

        # Invariant 2: exactly 21 unique (clip_id, target_index) keys
        target_audit = model_data["target_audit"]
        assert len(target_audit) == 21, f"{model_name} audit rows {len(target_audit)} != 21"
        keys = [(r["clip_id"], r["target_index"]) for r in target_audit]
        assert len(keys) == 21
        assert len(set(keys)) == 21, f"{model_name} has duplicate (clip_id, target_index) keys"

        # Verify outcome categories and exact sum
        outcomes = [r["outcome"] for r in target_audit]
        for o in outcomes:
            assert o in ("preserved", "inverted", "deleted", "ambiguous")
        from collections import Counter
        counts = Counter(outcomes)
        for cat in ("preserved", "inverted", "deleted", "ambiguous"):
            assert counts[cat] == tc[cat], f"{model_name} {cat} count mismatch: {counts[cat]} != {tc[cat]}"


def test_msv_published_union_reproduces_from_audit_rows():
    import csv
    from pathlib import Path
    audit_path = Path("bench/results/tier_a_multispeaker_validation_audit.csv")
    assert audit_path.is_file()
    with audit_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Group by (clip_id, target_index)
    by_target = {}
    for r in rows:
        key = (r["clip_id"], int(r["target_index"]))
        if key not in by_target:
            by_target[key] = {}
        by_target[key][r["model"]] = r["outcome"]

    assert len(by_target) == 21, f"Expected 21 unique targets, got {len(by_target)}"

    # Count a target in union only when at least one model has an adjudicated 'inverted' outcome
    union_inversions = 0
    uninverted_keys = []
    for key, model_outcomes in sorted(by_target.items()):
        if any(model_outcomes.get(m) == "inverted" for m in ("gemini", "deepgram", "whisper")):
            union_inversions += 1
        else:
            uninverted_keys.append((key, model_outcomes))

    # Exactly 20 of 21 unique targets inverted by at least one global model
    assert union_inversions == 20
    assert len(uninverted_keys) == 1
    # The single uninverted target is spk4_m_003 (prompt 3, target 1)
    assert uninverted_keys[0][0] == ("spk4_m_003", 1)
    assert uninverted_keys[0][1]["sahara"] == "preserved"
    assert uninverted_keys[0][1]["gemini"] == "ambiguous"
    assert uninverted_keys[0][1]["deepgram"] == "ambiguous"
    assert uninverted_keys[0][1]["whisper"] == "ambiguous"

    # Invariant from results.json
    results_path = Path("bench/results/tier_a_multispeaker_validation_results.json")
    data = json.loads(results_path.read_text(encoding="utf-8"))
    assert data["multi_model_union"]["union_inversions"] == 20
    assert data["multi_model_union"]["total_targets"] == 21
    assert abs(data["multi_model_union"]["union_inversion_rate"] - (20 / 21)) < 1e-6


