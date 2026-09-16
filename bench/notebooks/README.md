# Whisper Colab Benchmark Notebooks

This directory contains cloud-oriented Jupyter notebooks designed for execution on Google Colab GPU runtimes (T4 or A100).

## 1. Multi-Speaker Validation (Tier A-MSV)
- **Notebook:** [`whisper_msv_benchmark.ipynb`](file:///mnt/c/Users/USER/Documents/Sauticivic/bench/notebooks/whisper_msv_benchmark.ipynb)
- **Purpose:** Transcribes and adjudicates the 30 Tier A-MSV audio clips across 3 unseen Nigerian speakers (`SPK-03` Chinenye, `SPK-04` Daniel, `SPK-05` Mukhtar) using **OpenAI Whisper large-v3**.
- **Input Source:** Google Drive folders (`Chineye tier a audio`, `Daniel tier a audio`, `Mukthar tier a audio`) containing raw `.ogg` files.
- **Workflow:**
  1. Mounts Google Drive (`/content/drive`).
  2. Auto-locates the 3 speaker folders containing `.ogg` audio.
  3. Converts `.ogg` audio to canonical 16kHz mono WAV using `ffmpeg`.
  4. Runs Whisper `large-v3` inference with deterministic greedy decoding (`temperature=0.0`).
  5. Computes Word Error Rate (WER) and Pidgin completive aspect *don* $\to$ *don't* polarity inversion adjudication.
  6. Exports 30 schema-compliant JSON transcripts in `whisper_msv_transcripts.zip`.

## 2. Ingesting Transcripts Back into Sauticivic
Once the notebook run finishes and downloads `whisper_msv_transcripts.zip`:
1. Unzip the JSON files into:
   ```bash
   bench/results/transcripts/tier_a_multispeaker_validation/whisper/
   ```
2. Re-run the validation and analysis script to update the unified results and audit tables:
   ```bash
   python3 bench/metrics/run_tier_a_multispeaker_validation.py
   ```
3. Run tests to verify benchmark integrity:
   ```bash
   PYTHONPATH=backend pytest backend/tests/test_tier_a_multispeaker_validation.py
   ```
