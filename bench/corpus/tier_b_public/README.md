# Tier B Public Benchmark Corpus

This directory contains the ingestion infrastructure and metadata for the **Tier B Public Dataset Evaluation** in SautiCivic Bridge.

## 1. Overview & Strategy

While Tier A comprises 30 self-recorded, independently double-labeled code-switched audio clips evaluating the full end-to-end pipeline, Tier B expands the acoustic and linguistic evaluation across 60 clips from three established public speech datasets.

- **Target Count:** 60 clips total across 3 datasets and 4 language pairs.
- **Evaluation Scope:** ASR Word Error Rate (WER) and Named Entity Recognition / Recall only.
- **Duration Constraints:** Maximum duration 60.0s (longer clips trimmed to first 60s; never padded). Minimum duration 3.0s (shorter clips discarded).
- **Audio Specification:** 16 kHz mono, 16-bit signed PCM WAV, validated via `bench/audio_preprocessing/convert_and_validate.py`.

---

## 2. Datasets & Provenance

| Dataset | Source / HuggingFace URL | License | Clips | Language / Config | Clip Type | Selection Criteria |
|---|---|---|---|---|---|---|
| **AfriSwitch** | [`intronhealth/AfriSwitch`](https://huggingface.co/datasets/intronhealth/AfriSwitch) | CC BY-NC-SA 4.0 | 30 | Pidgin-English (10)<br>Yoruba-English (10)<br>Hausa-English (10) | Code-Switched | Top N sorted by Code-Mixing Index (`cmi`) descending |
| **FLEURS** | [`google/fleurs`](https://huggingface.co/datasets/google/fleurs) | CC BY 4.0 | 15 | Hausa `hau_NG` (8)<br>Yoruba `yor_NG` (7) | Accent | Sorted by transcript length descending |
| **AfriSpeech-200** | [`tobiolatunji/afrispeech-200`](https://huggingface.co/datasets/tobiolatunji/afrispeech-200) | CC BY 4.0 | 15 | Nigerian-accented English | Accent | Filter `accent_area == "Nigeria"`, sorted by transcript length descending |

---

## 3. Code-Switched vs. Accent Distinction

- **AfriSwitch (Code-Switched):** Specifically probes spontaneous, intra-sentential language alternation between English and major Nigerian languages (Pidgin, Yoruba, Hausa). Sidecar metadata records empirical CMI scores.
- **FLEURS & AfriSpeech (Accent Robustness):** Single-language utterances testing acoustic, dialectal, and named-entity transcription under authentic Nigerian speech contexts. Sidecar metadata explicitly records `clip_type: "accent"` and `cmi: null`.

---

## 4. Ground Truth & Labeling Policy

All three datasets provide published, peer-reviewed human transcriptions.
- Ground truth is taken directly from each dataset's canonical transcription field (`transcript`, `sentence`, or `transcription`).
- No re-transcription or secondary labeling is applied to Tier B public clips.
- Sidecar JSON files (`<clip_id>.json`) store individual ground truth transcripts and metadata alongside each WAV file.
- The consolidated ground truth file is [`ground_truth_tier_b.json`](file:///mnt/c/Users/USER/Documents/Sauticivic/bench/corpus/tier_b_public/ground_truth_tier_b.json).

---

## 5. What Tier B Proves vs. What It Cannot Prove

- **What Tier B Proves:** ASR acoustic and entity recognition generalization beyond our team's voices and scripts, evaluated across independent speakers and four language pairs.
- **What Tier B Cannot Prove:** End-to-end civic intake routing or downstream classification accuracy. Tier B clips lack municipal infrastructure and legal aid domain annotations; they are evaluated strictly for WER and entity recall. Full pipeline evaluation remains exclusively Tier A.

---

## 6. Usage & Ingestion

```bash
# Dry run (inspect plan and output directories without downloading)
python3 bench/corpus/tier_b_public/ingest_tier_b.py --dry-run

# Live ingestion of all datasets (Colab / cloud environment)
python3 bench/corpus/tier_b_public/ingest_tier_b.py --dataset all

# Ingest single dataset
python3 bench/corpus/tier_b_public/ingest_tier_b.py --dataset afriswitch --n-clips 10
```

### Whisper large-v3 Evaluation (Colab GPU)

To transcribe Tier B with Whisper `large-v3`, use the ready-to-run Colab notebook:
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Spyder0000/Sauticivic/blob/main/bench/whisper_tier_b_colab.ipynb)

Located at: [`bench/whisper_tier_b_colab.ipynb`](../whisper_tier_b_colab.ipynb)


---

## 7. Compliance & Terms of Use Disclaimer

> **Disclaimer:** Audio fetched at runtime for evaluation only. Not redistributed. Not used for training. Cited per each dataset's license terms.
