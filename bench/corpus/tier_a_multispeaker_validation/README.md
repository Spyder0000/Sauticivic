# Tier A Multi-Speaker Validation (Tier A-MSV)

This is a separate confirmatory Tier A dataset, not Tier B. It addresses the original Tier A speaker-diversity limitation by adding the same ten selected Nigerian Pidgin/English prompts from three previously unseen speakers: SPK-03 (female), SPK-04 (male), and SPK-05 (male).

The source filenames and prompt mappings were verified by the dataset provider. Speakers were instructed to read the canonical scripts, and all three speakers consented to recording and benchmark use. `spoken_reference_transcript` therefore uses the canonical script-based references. Spontaneous wording deviations were not independently audited; this limitation must be retained in interpretation. Speaker accent, device, and environment metadata are unavailable and represented as null.

Prompts 001--005 and 009 are polarity-stress prompts: 18 recordings contain 21 expected Pidgin `don` targets, because prompt 002 contains two occurrences. Prompts 006--008 and 010 are 12 controls. Expected domain/outcome labels match the original Tier A labels.

Audio is copied from the original source folders without modifying them and converted to mono 16 kHz 16-bit PCM WAV with ffmpeg. The final corpus is deterministic and frozen by `MANIFEST_SHA256.txt`.

Reproduction: `PYTHONPATH=backend python3 bench/metrics/run_tier_a_multispeaker_validation.py --prepare-corpus --validate-only`; model execution uses `--models sahara,gemini,deepgram,whisper` after the required credentials and local/cloud model dependencies are available. Results are additive and do not modify v19.
