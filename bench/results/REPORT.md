# SautiCivic Bridge — Benchmark Report

> **Technical benchmark report** (engineering-facing). The submission-facing
> summary lives in `docs/BENCHMARK_REPORT.md`. This file is the detailed,
> honest record of methodology, results, versioning, and known limitations.

---

## Status

| | |
|---|---|
| **Report version** | v2 |
| **Corpus** | Synthetic, text-only (Tier A **real audio not yet recorded**) |
| **Real ASR transcripts** | None yet — WER and per-model ASR-fault attribution are wired but report `not_available` |
| **Headline result** | **artifact-corrupted = 0%** — the abstain-gate produced zero corrupted artifacts |
| **Pipeline backends** | Mock keyword classifier + mock regex extractor (real LLM/ASR backends pending) |

**Read this first:** v2 is a **methodology and plumbing** bump on the *same*
synthetic corpus as v1 — not new empirical data. The headline downstream and
oracle numbers are **identical to v1** (same corpus, same pipeline). What
changed in v2 is (1) the corpus description is now derived from the data
instead of a stale hardcoded string, and (2) WER + per-model oracle attribution
are now wired into the orchestrator and will populate automatically the moment
real transcripts exist. See [Version History](#version-history).

---

## Corpus

| Property | Value |
|---|---|
| Total clips | 15 |
| Expected-routed | 11 (6 infrastructure, 5 legal) |
| Expected-abstain / ambiguous | 4 (`needs_clarification`) |
| Type | `synthetic_text_only` — hand-authored Nigerian-Pidgin/English code-switch transcripts |
| Real audio | **None** — Tier A recording (#1) not yet done |
| Frozen | `bench/corpus/tier_a_recorded/MANIFEST_SHA256.txt`, 2026-08-19T22:01:01Z |
| `ground_truth.json` SHA256 | `203ebf4bf57d0f0a686d566a66fd7942acbaf244b2aba889532a198dea9dad39` |

The corpus is **frozen** under SHA256 before any model run (design rule #4: no
clip added or dropped after seeing model results). The synthetic clips exercise
three cases the gate must handle: clearly-routable infrastructure complaints,
clearly-routable legal grievances, and genuinely ambiguous/under-specified
inputs where the correct behavior is to abstain and ask.

---

## Methodology

### The gate (the safety mechanism)

Every input flows through one choke point (`pipeline.run_intake()`) into a pure
confidence/completeness gate (`gate.py::decide()`). The gate fires
**abstain-and-ask** if either:

- classifier confidence `< τ` (**τ = 0.70**, default), or
- a required entity is missing / low-confidence (**entity τ = 0.60**) — e.g. a
  location for a municipal ticket, party names for a legal brief.

The design intent: **an abstention is a safe failure; a corrupted artifact is
not.** Driving `artifact-corrupted` toward 0% is the whole point, even at the
cost of some recall (false abstentions).

> **τ = 0.70 is tuned against the mock keyword classifier and is not
> calibrated for a real backend.** It must be re-derived empirically when the
> real classifier is wired in (design rule #2).

### Downstream accuracy (headline metric — `downstream_accuracy.py`)

| Metric | Definition |
|---|---|
| **classification-exact** | Of clips that *should* route, fraction where `actual_domain == expected_domain`. Denominator = expected-routed clips only. |
| **artifact-safe** | Fraction of clips where the pipeline produced *either* the correct artifact *or* no artifact (abstained) — i.e. never a wrong artifact. |
| **artifact-corrupted** | Fraction of clips where an artifact was generated for the **wrong** domain. **This is the number the gate exists to keep at 0.** |
| **abstention** | Fraction of clips the gate sent to `needs_clarification`, split into *correct* (genuinely ambiguous) vs *false* (should have routed). |

### Oracle-vs-ASR attribution (`run_oracle_comparison.py`)

For each clip the pipeline runs **twice** — once on the "ASR" transcript, once
on the ground-truth transcript — and every result is bucketed:

| Bucket | Meaning |
|---|---|
| `concordant_correct` | Both runs agree and are correct |
| `concordant_incorrect` | Both agree but are wrong → **reasoning/classifier fault** |
| `asr_fault` | Oracle run correct, ASR run wrong → **transcription caused the failure** |
| `reasoning_fault` | Oracle run wrong, ASR run right (unusual) |

> **Current limitation:** with no real ASR model, the ground-truth transcript is
> used as *both* the ASR and the oracle input, so `asr_fault = 0` **by
> construction**. This run validates the bucketing *logic*, not a real
> ASR-vs-reasoning split. The per-model wiring (`oracle_comparison_by_model`) is
> in place and activates automatically once real transcripts land — no code
> change required.

### Word Error Rate (`wer.py`)

Corpus-level WER via Levenshtein edit distance, weighted by reference word
count, computed after a **conservative Naija-contraction normalization** pass.
The orchestrator reports one normalized corpus WER per model against the
ground-truth reference; per-clip raw (un-normalized) WER is available via
`wer.wer(..., normalize_text=False)`.

> **The normalization table is lossy by design** — see
> [Known Issues (d)](#known-issues). It expands contractions approximately
> (e.g. `no→not`, `na→is`, `e→it`, `dey→is`); this is a documented scoring
> choice, not a defect.

---

## Results (v2)

### Downstream accuracy

| Metric | Value |
|---|---|
| Total clips | 15 |
| **Classification-exact** | **90.9%** (10 / 11 expected-routed) |
| **Artifact-safe rate** | **100.0%** |
| **Artifact-corrupted rate** | **0.0%** (count = 0) |
| Abstention rate | 33.3% (5 / 15) |
| — correct abstentions | 4 |
| — false abstentions | 1 |
| Total routed | 10 |
| Total abstained | 5 |

**The headline holds: 0% artifact-corrupted.** No wrong artifact was generated
for any clip. The single classification miss (`synth_013`,
*"My neighbour contractor refuse to pay the labourers dem for the work wey dem
do"* — expected `legal`) did **not** produce a corrupted artifact: the gate
abstained on it instead. That is the intended trade-off — one false abstention
(a recall cost) rather than one corrupted legal brief (a safety failure).

### Oracle-vs-ASR attribution (baseline — ground-truth as both ASR & oracle)

| Bucket | Count |
|---|---|
| `concordant_correct` | 14 |
| `concordant_incorrect` | 1 |
| `asr_fault` | 0 *(by construction — no real ASR)* |
| `reasoning_fault` | 0 |

| Abstention correlation | Count |
|---|---|
| Total abstentions | 5 |
| Warranted (expected abstain) | 4 |
| Unwarranted (should have routed) | 1 |

The single `concordant_incorrect` is `synth_013` — a real classifier/reasoning
limitation of the mock keyword backend (a labour-dispute framed without the
keywords the mock keys on), reproducible on the clean transcript. It is **not**
an ASR artifact.

### Word Error Rate

**`not_available`** — the synthetic corpus has no audio, so no model produced
transcripts. WER is wired per model (`sahara`, `whisper`, `deepgram`) and
activates automatically once transcripts appear in
`bench/results/transcripts/<model>/`.

### Per-model oracle attribution

**`not_available`** — same reason. `oracle_comparison_by_model` is wired to feed
each model's real transcripts into the ASR run, which is what makes `asr_fault`
meaningful. Zero code change needed when transcripts land.

---

## Version History

Per design rule #3, every methodology or preprocessing fix gets a new versioned
results file (`vN_results.json`) with a documented before/after delta — never a
silent overwrite.

| Aspect | v1 | v2 | Why it changed |
|---|---|---|---|
| Downstream numbers | 90.9% / 100% / **0%** | 90.9% / 100% / **0%** | **Unchanged** — same corpus, same pipeline. v2 is a plumbing/methodology bump, not new data. |
| Oracle baseline buckets | 14 / 1 / 0 / 0 | 14 / 1 / 0 / 0 | **Unchanged** — same reason. |
| Corpus description | Hardcoded string: *"9 routed (5 infra, 4 legal), 4 abstain, 2 edge"* — **stale, drifted from data** | Derived from the corpus at runtime: *"11 routed (6 infra, 5 legal) + 4 needs_clarification"* | The v1 string was hand-written and no longer matched the actual 15 clips. v2 computes counts from the data so it can never drift again. |
| WER | Absent from orchestrator | Wired per model; reports `not_available` until transcripts exist | Completes the benchmark harness (#4 wiring). |
| Per-model oracle | Baseline only (gt-as-both) | Baseline **+** per-model real-ASR wiring (`oracle_comparison_by_model`) | Makes `asr_fault` meaningful the instant real transcripts land. |
| `known_limitations` | 5 items | 6 items (added WER-normalization caveat, refined oracle note) | Honesty about the new WER scoring choice. |

**v3 (pending):** real Tier A audio + real ASR transcripts → real WER and real
per-model `asr_fault`. See [What Unblocks v3](#what-unblocks-v3).

---

## Known Issues

Stated plainly — benchmark rigor is what's scored (design rule #5), and that
includes being honest about what these numbers do and don't mean.

**(a) Synthetic corpus, no real ASR.** All 15 clips are hand-authored text.
There is no recorded audio and no real transcription, so every number here
measures the *reasoning/gate* half of the pipeline on clean input. It says
nothing yet about real-world ASR error on code-switched speech.

**(b) Mock classifier + mock extractor.** The classifier is keyword-based
(confidence = keyword hit ratio, not a calibrated probability) and the extractor
is regex-based. Real LLM/Sahara-driven backends will change both the accuracy
and the confidence distribution the gate keys on.

**(c) `asr_fault = 0` by construction.** Because ground-truth is used as both
ASR and oracle input, the ASR-vs-reasoning split is not yet meaningful. The
wiring is done; only real transcripts are missing.

**(d) WER normalization is lossy by design.** The Naija-contraction expansion
table in `wer.py` is *approximate*: it maps, among others, `no→not`, `na→is`,
`e→it`, `dey→is`, `dem→them`, `wetin→what`, `abeg→please`, `nepa→electricity`.
These collapse legitimate distinctions (e.g. Pidgin `no` as negation vs. English
"no") and will slightly distort WER on genuinely code-switched text. This is a
**documented scoring choice** to make WER comparable across models, not a bug —
but it must be revisited with linguist input before WER is used to rank models.

**(e) τ = 0.70 / entity τ = 0.60 are tuned to the mock.** The thresholds are
fitted to the placeholder keyword-matcher's score distribution. They must be
re-derived empirically against the real classifier before v3 conclusions.

---

## Sahara Contingency (Whisper fallback)

Sahara v2.5 API access is **not yet confirmed** (ARCHITECTURE open items;
TASK_SPLIT #27). The harness is built so this is a **zero-code swap**: all three
model runners (`run_sahara.py`, `run_whisper.py`, `run_deepgram.py`) write the
*same* transcript JSON schema to `bench/results/transcripts/<model>/`, and the
metric layer reads all three identically. If Sahara access slips,
`run_whisper.py` (large-v3) is the fallback ASR and `run_sahara.py` already
degrades to a Whisper backend. The benchmark does not depend on any single
provider being available.

---

## What Unblocks v3

- [ ] **Record Tier A audio** from native code-switch speakers, with consent (#1)
- [ ] **Two independent labelers** → dual ground truth + inter-annotator agreement (`inter_annotator_agreement.py`, #2)
- [ ] **Confirm Sahara v2.5 API** surface/auth — or commit to the Whisper fallback (#15 / #27)
- [ ] **Set up Deepgram Nova-3** API key (#10)
- [ ] **Run `convert_and_validate.py` on Colab** → verified 16 kHz mono 16-bit WAVs + A/B report (#5)
- [ ] **Run the model runners on Colab** (`run_sahara`, `run_whisper`, `run_deepgram`) → commit transcripts back (#9, #10, #15)
- [ ] **Re-run `run_full_benchmark.py` locally** → `v3_results.json` with real WER + real `asr_fault`
- [ ] **Re-derive τ** against the real classifier's confidence distribution (#11)

---

## How to Reproduce

```bash
# Text-only metrics — run locally (no audio, no GPU):
cd backend && python3 -m pytest                      # unit tests (gate, pipeline)
PYTHONPATH=backend python3 -m bench.metrics.run_full_benchmark   # writes vN_results.json

# Audio model runs — run on Colab / cloud (see ARCHITECTURE.md § Compute Environment):
python3 bench/audio_preprocessing/convert_and_validate.py --input-dir ... --output-dir ...
python3 bench/models/run_whisper.py  --corpus ... --output-dir bench/results/transcripts
python3 bench/models/run_deepgram.py --corpus ... --output-dir bench/results/transcripts
python3 bench/models/run_sahara.py   --corpus ... --output-dir bench/results/transcripts
# commit bench/results/transcripts/<model>/ back, then re-run run_full_benchmark locally
```

*Machine-readable results: `bench/results/v2_results.json` (this report's source
of truth). Prior version: `bench/results/v1_results.json`.*
