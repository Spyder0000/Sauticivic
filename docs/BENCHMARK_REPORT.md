---
title: "SautiCivic Bridge: A Safety-Critical Speech Benchmark for Code-Switched Nigerian Civic Grievance Intake"
subtitle: "Sahara CodeSwitch Africa Challenge 2026 — Legal & Public Services Track | Technical Benchmark Report v20 Addendum"
date: "September 2026"
geometry: "margin=1.6cm"
fontsize: 9pt
documentclass: extarticle
linestretch: 1.05
---

# 1. Executive Summary

Automated voice intake pipelines for municipal public works and frontline legal aid clinics in West Africa confront a severe structural hurdle: citizens naturally report grievances through code-switching between Nigerian Pidgin (Naija, an English-lexified Creole) and standard English, rather than monolingual standardized registers. We present the v19 benchmark evaluation of four diverse production speech engines---Intron Sahara v2.5, Google Gemini 3.5 Transcribe, Deepgram Nova-3, and OpenAI Whisper large-v3---across 30 in-domain scripted grievance recordings (Tier A) and 60 out-of-domain public African speech clips (Tier B).

Our central empirical discovery is that standard Word Error Rate (WER) exhibits a catastrophic blind spot in safety-critical governance: it entirely masks **aspectual polarity inversion**. General-purpose commercial and open-source baselines systematically transcribe the Nigerian Pidgin completive aspect marker *don* (glossed PERF, denoting completed reality) as the standard English negative contraction *don't*, reversing affirmative citizen grievances into explicit denials in 16.7% to 40.0% of scripted complaints. **Sahara v2.5 is the only evaluated system to achieve a 0.0% inversion rate (0/30)**, showing complete preservation of the evaluated target markers in this sample. Gemini produced polarity inversions in 5/30 Tier A complaints despite having WER close to Sahara, which could render the complaint non-actionable, incorrectly classified, or unsafe for automated routing without an uncertainty gate. Integrated into the end-to-end SautiCivic intake architecture, our deterministic two-tier risk gate achieves a **100.0% safe outcome rate** (17/17 safe emitted artifacts, 13/13 safely abstained) and **100.0% adversarial harm-avoidance (10/10)**, safely intercepting simulated compound legal-criminal test traps where unconstrained routing would generate flawed artifacts.

# 2. Models and Corpus

Four production backends were evaluated on identical acoustic inputs across two testing tiers.

Table 1: Evaluated ASR architectures and benchmark corpus distribution.

| Model | Architectural Archetype | Tier A | Tier B | Optimization & Linguistic Priors |
|:------|:------------------------|:------:|:------:|:---------------------------------|
| **Sahara v2.5** | Commercial African-Specialized | 30 | 60 | Acoustic/LM priors tuned for West African bilingual code-switching |
| **Gemini 3.5 Transcribe** | Commercial Multimodal Flagship | 30 | 60 | Web-scale semantic priors, strong entity normalization |
| **Deepgram Nova-3** | Commercial Global Speech Engine | 30 | 60 | Low-latency global English optimization, strict phonetic decoding |
| **Whisper large-v3** | Open-Source Multilingual Transformer | 30 | 60 | 680k-hour weakly supervised multilingual pre-training |

- **Tier A In-Domain Scripted Corpus:** 30 consented recordings of realistic Nigerian Pidgin/English grievance scenarios (16 kHz, 16-bit mono WAV) produced under documented informed consent (`DATA_CONSENT_LOG.md`) across two native speakers: SPK-01 (Lagos Yoruba-Pidgin substrate) and SPK-02 (Edo-Pidgin substrate). The corpus contains 20 expected-routed scenarios (10 municipal infrastructure, 10 legal aid) and 10 expected-abstain edge cases (`needs_clarification`). All clips are validated via dual-decoder checks and frozen with SHA-256 integrity hashes.
- **Tier B Out-of-Domain Generalization Suite:** 60 public speech clips across three distinct benchmarks: (1) *AfriSwitch* (30 clips across Pidgin-English, Yoruba-English, and Hausa-English, sorted by descending Code-Mixing Index / CMI); (2) *AfriSpeech-200* (15 clips of Nigerian-accented clinical English); and (3) *FLEURS* (15 clips of monolingual read Hausa and Yoruba).

# 3. Tier A Primary Results

WER alone is insufficient for civic ASR evaluation. Three additional metrics were recorded: polarity inversion rate (meaning reversal via *don*/*don't* confusion, which silently corrupts complaint semantics), hallucination rate (outputs exhibiting complete phonetic collapse or cross-language fabulation), and ASR faults (clips where ASR error causes incorrect downstream routing, identified via oracle comparison against ground-truth transcripts). Table 2 presents full Tier A results.

Table 2: Tier A benchmark evaluation across 30 in-domain scripted grievance recordings.

| Model | Corpus WER | Polarity Inversions | Inversion Rate | Hallucinations | ASR Faults | Concordant Correct |
|:------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sahara v2.5** | **12.4%** | **0 / 30** | **0.0%** | **0 / 30 (0.0%)** | **3** | **24 / 30 (80.0%)** |
| Gemini 3.5 Transcribe | 14.8% | 5 / 30 | 16.7% | 1 / 30 (3.3%) | 2 | 25 / 30 (83.3%) |
| Deepgram Nova-3 | 39.0% | 12 / 30 | 40.0% | 0 / 30 (0.0%) | 4 | 23 / 30 (76.7%) |
| Whisper large-v3 | 47.9% | 9 / 30 | 30.0% | 4 / 30 (13.3%) | 9 | 18 / 30 (60.0%) |

**The WER Insufficiency Paradox:** A superficial assessment based solely on WER ranks Gemini 3.5 (14.8%) as nearly equivalent to Sahara v2.5 (12.4%)---a mere 2.4 percentage-point delta. However, the aspectual polarity audit demonstrates that this metric proximity is an evaluation illusion. Gemini produced polarity inversions in 5/30 Tier A complaints despite having WER close to Sahara, which could render the complaint non-actionable, incorrectly classified, or unsafe for automated routing without an uncertainty gate. Sahara inverted none. Standard ASR leaderboards completely overlook this semantic inversion failure mode.

# 4. Tier A Multi-Speaker Validation

To evaluate the consistency of aspectual polarity inversion beyond the initial two-speaker corpus, we conducted a targeted confirmatory evaluation across three previously unseen speakers, including one female and two male speakers: SPK-03 (female), SPK-04 (male), and SPK-05 (male). Each recorded ten scripted prompts (30 clips total), yielding 18 polarity-stress clips (21 target tokens of Pidgin completive aspect marker *don*) and 12 controls. Regional accent metadata is unverified in corpus records. All models were evaluated on identical audio from cached offline transcripts; original v19 results remain frozen.

Table 3: Tier A-MSV aspectual polarity inversion results across three previously unseen speakers.

| Model | SPK-03 (F) | SPK-04 (M) | SPK-05 (M) | Token Inversions | Affected Utterances | MSV WER |
|:------|:----------:|:----------:|:----------:|:----------------:|:-------------------:|:-------:|
| **Sahara v2.5** | **0 / 7 (0.0%)** | **0 / 7 (0.0%)** | **0 / 7 (0.0%)** | **0 / 21 (0.0%)** | **0 / 18 (0.0%)** | **16.3%** |
| Gemini 3.5 Transcribe | 4 / 7 (57.1%) | 2 / 7 (28.6%) | 4 / 7 (57.1%) | 10 / 21 (47.6%) | 9 / 18 (50.0%) | 28.7% |
| Deepgram Nova-3 | 4 / 7 (57.1%) | 2 / 7 (28.6%) | 4 / 7 (57.1%) | 10 / 21 (47.6%) | 9 / 18 (50.0%)\* | 68.9% |
| Whisper large-v3 | 2 / 7 (28.6%) | 5 / 7 (71.4%) | 4 / 7 (57.1%) | 11 / 21 (52.4%) | 10 / 18 (55.6%) | 111.7%\dagger |

*\*Deepgram affected-utterance rate is 9/18 (50.0%) across all 18 evaluated polarity clips with 1 token deletion (spk4_m_004) reported separately; previously reported as 9/17 when an empty output clip was omitted from the denominator.*  
*\dagger Whisper MSV WER reflects repetitive non-Latin script hallucinations (10/30 clips). Normalized WER (111.7%) exceeds raw WER (102.0%) because text normalizer character/diacritic separation inflates insertion counts (219 insertions across corpus).*

**Empirical Replication & Baseline Reconciliation:** Sahara produced 0/21 target-token inversions; 21/21 preserved, replicating the original Tier~A finding across three previously unseen speakers, including one female and two male speakers (regional accent metadata remains unverified in corpus records). General-purpose commercial and open-source baselines exhibited high inversion rates: Sahara produced 0/21 target-token inversions. Gemini and Deepgram each produced 10/21, while Whisper produced 11/21 on this targeted validation set. At least one of the three general-purpose baselines inverted each of 20 of the 21 unique targets (95.2% union result; model outputs are not pooled as independent population samples).

**Baseline Four-Category Reconciliations:** Deepgram produced 10 inversions, 1 preserved target, 1 deleted target (`spk4_m_004` empty output), and 9 ambiguous tokens, summing exactly to 21. Across all 30 Whisper recordings, 10 exhibited non-Latin hallucinations (6 target recordings, 4 control recordings). Among the 21 target occurrences, Whisper produced 11 inversions, 1 preserved target, 0 deleted targets, and 9 ambiguous tokens (7 attributed to non-Latin hallucinations, 1 cross-language collapse, and 1 acoustic verb corruption), likewise summing to 21. For `synth_002`, canonical prompt text (*"Water don burst for our street since morning, everywhere don flood."*) is preserved alongside verified spoken reference transcripts; WER evaluation strictly uses verified spoken references.

# 5. Polarity Mechanics and Qualitative Audit

In West African creole linguistics, *don* serves as an indispensable preverbal completive/perfective aspect marker denoting that an action or hazard has definitively occurred (analogous to English *"has/have done"*). One plausible explanation is that general-purpose decoding priors favor the high-frequency English contraction *don't* over the Nigerian Pidgin completive construction *[subject] don [verb]*. The present benchmark identifies the recurring failure pattern but does not establish its internal model-level cause.

**synth_001** (Municipal Pothole): Ground truth *"...e don spoil plenty tyre"* was preserved by Sahara (*"...e don spoil plenty tire"*), but inverted to negative denial (*"don't spoil"*) by Gemini, Deepgram, and Whisper.

**synth_024** (Domestic Abandonment & Eviction — High-Stakes Legal Aid Scenario):
- **Ground Truth:** *"My husband don chase me and the children comot for house, refuse to give us money for feeding."*
- **Sahara v2.5:** `"My husband don chase me and the children comot for house refuse to give us money for feeding"` [Preserved]
- **Gemini 3.5:** `"My husband don't chase me and the children come out for house, refuse to give us money for feeding."` [INVERTED]
- **Deepgram:** `"My husband don't chase me and the children come off our house, refuse to give us money for feeding"` [INVERTED]
- **Whisper v3:** `"my husband and daughter chase me and children come up for house refuse or give us money for food"` [Syntactic Collapse]
- **Sociotechnical Harm Analysis:** In this high-stakes domestic-abuse, eviction, and abandonment scenario, both Gemini and Deepgram invert affirmative abandonment into negative denial (*"don't chase"*), which could render the complaint non-actionable, incorrectly classified, or unsafe for automated routing without an uncertainty gate.

**Hallucination Pathology:** Tier A hallucinations occurred in 5/120 outputs: Whisper (4/30, 13.3%) and Gemini (1/30, 3.3%). Gemini's shift to French-like text and Whisper's phonetic collapse show why WER and language-validity audits must accompany polarity checks.

# 6. Tier B Generalization

Tier B tests generalization across 60 public African speech clips spanning code-mixing density, regional accents, and monolingual speech.

Table 4: Tier B Word Error Rate across public African speech benchmarks.

| Model | AfriSpeech (15) | FLEURS (15) | AfriSwitch (30) | Aggregate (60) | Named Entity Recall |
|:------|:---:|:---:|:---:|:---:|:---:|
| **Gemini 3.5 Transcribe** | 25.6% | **36.4%** | **35.6%** | **34.2%** | **92.3%** |
| **Sahara v2.5** | **23.2%** | 94.5% | 67.2% | 67.5% | 91.7% |
| **Whisper large-v3** | 30.6% | 93.7%\* | 68.2% | 68.5% | **92.3%** |
| **Deepgram Nova-3** | 40.1% | 100.0%\dagger | 73.5% | 75.4% | 90.8% |

Table 5: AfriSwitch intra-sentential code-switching WER by language pair (10 clips each).

| Model | Pidgin-English | Yoruba-English | Hausa-English | AfriSwitch Aggregate |
|:------|:---:|:---:|:---:|:---:|
| **Sahara v2.5** | **22.8%** | 79.4% | 87.8% | 67.2% |
| **Gemini 3.5 Transcribe** | 25.3% | **45.8%** | **36.0%** | **35.6%** |
| **Whisper large-v3** | 31.0% | 81.7% | 88.8%\ddagger | 68.2% |
| **Deepgram Nova-3** | 35.6% | 81.3% | 92.7% | 73.5% |

*\*Whisper FLEURS excludes 2 clips due to cross-script hallucination. \dagger Deepgram FLEURS 100.0% reflects word deletion (69.5% dropout). \ddagger Whisper AfriSwitch excludes `afriswitch_hau_008` for Ethiopic hallucination. Some Whisper subgroup WER values use reduced denominators after cross-script failures (51/60 scored overall), so direct aggregate comparison should be interpreted alongside model coverage rather than as fully like-for-like.*

**Linguistic & Architectural Takeaways from Tier B:**
1. **Engine Complementarity:** Gemini achieved the lowest aggregate Tier B WER (34.2%) and high named-entity recall; the benchmark does not isolate the internal cause. Sahara leads on Pidgin-English (22.8%) where creole syntax dominates. These complementary results motivate future evaluation of a Sahara-primary, constrained Gemini entity-fallback design.
2. **Domain Specialization Boundary:** Sahara's elevated FLEURS WER (94.5%) reflects an architectural boundary: Sahara v2.5 is optimized for bilingual code-switching; formal monolingual read Hausa/Yoruba constitutes an out-of-domain distribution.
3. **Deletion vs. Hallucination Modes:** Deepgram’s 100.0% FLEURS WER stems from phoneme suppression (69.5% word deletion), emitting zero non-English words. In contrast, Whisper hallucinates non-Latin scripts (Ethiopic characters), breaking downstream parsers.

# 7. Pipeline Safety

The SautiCivic intake architecture routes transcribed complaints through a deterministic two-tier safety gate (`gate.py`). In safety-critical civic intake, *an abstention is a safe failure, but a corrupted dispatch artifact is a catastrophic failure*. Table 6 summarizes downstream routing integrity.

Table 6: SautiCivic Bridge downstream routing, calibration, and safety metrics (v19 frozen baseline).

| Metric | v19 Result | Operational Interpretation & Benchmark Bar |
|:-------|:---:|:-------------------------------------------|
| **Safe Outcome Rate** | **100.0% (30/30)** | Safe route, safe artifact, or justified abstention across all 30 evaluated inputs. |
| **Emitted-Artifact Integrity** | **100.0% (17/17)** | 17/17 emitted artifacts (10 municipal tickets, 7 legal briefs) matched benchmark expectations and passed deterministic artifact checks. |
| **Corrupted-Artifact Escape** | **0.0% (0/17)** | Zero corrupted tickets or legal briefs escaped to downstream service channels (0/30 across all inputs). |
| **Classification-Exact** | **85.0% (17/20)** | Correct categorization on unambiguous grievances (10 infrastructure, 7 legal; 3 false abstentions). |
| **Abstention Rate** | 43.3% (13/30) | 10 justified abstentions on ambiguous inputs; false abstentions conservative (3/20). |
| **Adversarial Harm-Avoidance** | **100.0% (10/10)** | 10/10 intentional adversarial test traps neutralized in simulated evaluation; 0 high-severity gate breaches. |
| **Expected Calibration Error** | 30.9% | Baseline heuristic classifier; indicates weak confidence calibration under mock scoring. |
| **Speaker Voice Equity** | 90.9% vs 77.8% | SPK-01 (90.9%) vs SPK-02 (77.8%); confounded by clip complexity (see Section 8). |

**The Two-Tier Risk Interceptor Architecture:**
- **Tier 1 --- Life-Safety Interceptor:** Scans transcription streams for acute threats to life (active fires, explosions, chemical spills). Blocks ordinary artifact dispatch and returns an emergency-escalation recommendation, including guidance to contact 112, bypassing municipal and civil queues.
- **Tier 2 --- Criminal & Extortion Interceptor:** Evaluates complaints bound for municipal works. If compound lexical signals indicate unlawful coercion, taskforce extortion, armed violence, or tenancy lockouts, infrastructure ticket dispatch is force-blocked to prevent misrouting.
- **Operational Thresholding & Fallbacks:** The pipeline enforces confidence thresholds ($\tau \ge 0.70$). Inputs falling below $\tau$ or missing required entities trigger automated clarification flows rather than guessing citizen intent.

**Neutralization of Adversarial Traps (10/10 Verified in Simulated Evaluation):** All ten distinct adversarial test scenarios in `bench/corpus/adversarial_cases.json` were neutralized by the Two-Tier Risk Gate in simulated evaluation:
1. `adv_003` (State Demolition & Extortion): Demolition masked as rubble clearing; blocked by Tier 2 criminal demolition logic to prevent misrouting.
2. `adv_004` (Workplace Fire & Chained Exit): Chained exit during wage dispute; intercepted by Tier 1 life-safety rules, blocking ordinary dispatch and recommending emergency escalation to 112.
3. `adv_005` (Vigilante Assault at Borehole): Violent assault at public tap; intercepted by criminal violence cues, suppressing tap repair dispatch.
4. `adv_001`, `adv_007`, `adv_009` (Domestic Violence, Land Grab, Acid Spill): Masked drainage dump, armed land demolition, and acid spill safely suppressed from standard sanitation dispatch.

# 8. Ethics and Limitations

**Societal Impact & Linguistic Context:** Nigerian Pidgin is used by millions of speakers and serves as a widely used lingua franca. When commercial foundation models convert affirmative completive markers (*don*) into English negative contractions (*don't*), citizens reporting broken water mains, power failures, or tenancy crises risk having their reports recorded as denials, which could render complaints non-actionable, incorrectly classified, or unsafe for automated routing without an uncertainty gate. By validating localized speech models like Sahara alongside deterministic safety gates, SautiCivic Bridge supports an equitable intake standard.

**Data Protection & Consent:** The evaluation uses pseudonymous speaker IDs (`SPK-01`--`SPK-05`), documented consent (`DATA_CONSENT_LOG.md`), restricted benchmark access, and PII-minimized metadata. Because voice recordings may themselves be identifying, raw audio requires controlled access and retention. Public reports do not expose private speaker names.

**Scientific Disclosures & Known Limitations:** Five explicit limitations are disclosed:
1. **Confidence Calibration:** The 30.9% ECE indicates weak confidence calibration under the heuristic classifier. It should not be interpreted as deployment-grade calibration.
2. **Speaker Equity Confound:** The performance difference between SPK-01 (90.9%) and SPK-02 (77.8%) is confounded with clip difficulty: SPK-02 was allocated 50% more ambiguous grievances (40.0% vs. 26.7%). It cannot be interpreted as an intrinsic voice disparity.
3. **Single-Labeler Baseline:** Tier A ground-truth references were established by a single expert labeler due to challenge timeline constraints.
4. **AfriSwitch Denominators & Provenance:** Upstream identifiers were added in v19 to eliminate transcript misalignment. Some Whisper subgroup WER values use reduced denominators after cross-script failures (51/60 scored overall).
5. **MSV Sample Composition:** MSV replicated the observed polarity pattern across three additional speakers. Its one-female/two-male composition is insufficient for gender fairness conclusions, and regional accent metadata remains unverified.

# 9. Reproducibility

The complete benchmark suite is reproducible via the following commands executed from the repository root, all operating entirely offline from cached transcripts and test manifests without calling paid APIs:
- **Unit & Safety Tests:** `PYTHONPATH=backend python3 -m pytest backend/tests/` (validates 55 tests: gate logic, schema integrity, and raw transcript immutability).
- **Corpus Ingestion & v19 Baseline:** Verify frozen hash `sha256sum bench/results/v19_results.json` matches `c3cb688...` (full hash: `c3cb68824f70a231dd05f776de423042b02e750175c917e4367d82a108c127b8`); recomputed via `PYTHONPATH=backend python3 -m bench.metrics.run_full_benchmark`.
- **Multi-Speaker Validation (MSV):** `python3 bench/metrics/run_tier_a_multispeaker_validation.py` (clause-aware polarity adjudication across SPK-03, SPK-04, and SPK-05 from cached transcripts).
- **Polarity Stress Analysis:** `python3 bench/metrics/polarity_stress_analysis.py` (generates clip audit to `bench/results/tier_a_multispeaker_validation_audit.csv`).
