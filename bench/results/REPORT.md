# SautiCivic Bridge — Benchmark Report

> **Technical benchmark report** (engineering-facing). The submission-facing
> summary lives in `docs/BENCHMARK_REPORT.md`. This file is the detailed,
> honest record of methodology, results, versioning, and known limitations.

---

## Status

| | |
|---|---|
| **Report version** | v7 |
| **Date** | 2026-09-03 |
| **Corpus** | Tier A recorded audio (30 clips across 2 native Nigerian Pidgin speakers; Tier B expanded field audio pending) |
| **Real ASR transcripts** | Executed across 4 production models (Sahara v2.5, Gemini 3.5 Transcribe, Deepgram Nova-3, Whisper large-v3) |
| **Headline result** | **artifact-corrupted = 3.3%** (1/30), **artifact-safe = 96.7%** (29/30) |
| **Downstream routing** | **classification-exact = 70.0%** (14/20 expected-routed), **abstention = 50.0%** (15/30) |
| **Pipeline backends** | Real 4-model ASR evaluation + downstream safety gate audit (mock classifier baseline; LLM/Sahara-driven reasoning in progress) |

**Read this first:** v7 is the **finalized empirical evaluation** on the full Tier A
corpus of 30 code-switched Nigerian Pidgin and English audio clips. All four
ASR engines (Sahara v2.5, Gemini 3.5 Transcribe, Deepgram Nova-3, Whisper large-v3)
have been executed on real audio inputs. Downstream classification, entity extraction,
confidence calibration, speaker voice equity, and adversarial stress-tests have been
audited and cross-tabulated against ground truth. See [Version History](#version-history).

---

## Corpus

| Property | Value |
|---|---|
| Total clips | 30 |
| Expected-routed | 20 (10 infrastructure, 10 legal) |
| Expected-abstain / ambiguous | 10 (`needs_clarification`) |
| Type | `tier_a_recorded` — authentic recorded speech in Nigerian Pidgin / English code-switch |
| Real audio | **30 clips** (15 clips SPK-01 Agoro Timilehin, 15 clips SPK-02 David Akhuabe) |
| Audio specs | 16 kHz mono 16-bit WAVs validated via `convert_and_validate.py` |
| Frozen | `bench/corpus/tier_a_recorded/MANIFEST_SHA256.txt` |
| `ground_truth.json` SHA256 | Verified frozen ground truth |

The corpus is **frozen** under SHA256 before any model run (design rule #4: no
clip added or dropped after seeing model results). The clips exercise
three primary operational cases: clearly-routable infrastructure complaints,
clearly-routable legal grievances, and genuinely ambiguous/under-specified
inputs where the correct civic intake behavior is to abstain and ask.

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

## Results & Discussion (v7)

### Section 1: Quantitative Results Table

The Tier A evaluation benchmarked all 30 authentic code-switched audio recordings across four production ASR engines. Downstream evaluation passed both ground truth and raw ASR hypotheses through the SautiCivic intake pipeline (`pipeline.run_intake()`) and safety gate (`gate.py`).

| Model | Corpus WER | Polarity Inversion Rate | Hallucination Rate | ASR Faults | Concordant Correct |
|---|---|---|---|---|---|
| **Sahara v2.5** | **12.4%** (0.1244) | **0.0%** (0/30) | **0.0%** (0/30) | **2** | **21 / 30** |
| **Gemini 3.5 Transcribe** | **14.8%** (0.1479) | **16.7%** (5/30) | **3.3%** (1/30) | **2** | **21 / 30** |
| **Deepgram Nova-3** | **39.0%** (0.3897) | **43.3%** (13/30) | **6.7%** (2/30) | **4** | **19 / 30** |
| **Whisper large-v3** | **47.9%** (0.4789) | **36.7%** (11/30) | **13.3%** (4/30) | **8** | **15 / 30** |

*Note: Total word count across the 30-clip corpus is 426 words. Total edit distance: Sahara = 53 (6 ins, 18 del, 29 sub); Gemini = 63 (7 ins, 3 del, 53 sub); Deepgram = 166 (11 ins, 24 del, 131 sub); Whisper = 204 (40 ins, 6 del, 158 sub). Concordant incorrect count across all models is 7/30, reflecting baseline mock classifier heuristics on dual-intent complaints.*

---

### Section 2: WER Insufficiency — Why Surface Accuracy Misleads

A benchmark reporting only WER would have rated Gemini 3.5 Transcribe as equivalent to Sahara v2.5 on this corpus. Our downstream polarity audit reveals this equivalence is a measurement artifact.

On raw word edit distance, Gemini 3.5 Transcribe (14.8% WER) appears virtually indistinguishable from Sahara v2.5 (12.4% WER) — separated by only 10 edit operations across 426 words. However, analyzing *which* words were altered exposes diametrically opposed error profiles:
- **Sahara v2.5's errors** are phonetic spelling approximations on named landmarks (`"aleena venue"` for *"Allen Avenue"*, `"poto"` for *"pothole"*, `"gbega"` for *"berger"*), while leaving 100% of Pidgin functional morphemes and tense/aspect markers syntactically intact.
- **Gemini 3.5 Transcribe's lower WER** is purchased through aggressive entity standardization and English lexical normalization. In exchange, Gemini systematically corrupts West African creole aspectual particles into English negations. A 2.4% WER delta between Sahara and Gemini masks a catastrophic 16.7% vs. 0.0% safety risk gap.

In civic governance systems, an orthographic typo in a street name is easily resolved by a human operator or geographic resolver, but an inverted aspectual particle changes the legal meaning of the citizen's grievance entirely.

---

### Section 3: Polarity Inversion — A Civic Safety Failure Class

Polarity inversion occurs when a model transcribes the Nigerian Pidgin completive aspect marker 'don' as the English negative contraction 'don't', reversing the logical polarity of the complaint.

In West African creole linguistics, *"don"* functions as an affirmative completive/perfective aspect marker indicating that an action has definitively occurred (analogous to *"has/have done"*). Commercial speech engines trained primarily on standard English acoustic-language distributions lack an aspectual prior for *"don"* and force the acoustic signal into the high-frequency English negative auxiliary *"don't"*.

This represents a distinct, novel finding — not a generic transcription error. It systematically inverts the citizen's complaint from an affirmative report of harm into an explicit denial of harm.

#### Verbatim Side-by-Side Comparisons:

#### 1. `synth_001` (Municipal Infrastructure — Road Hazard)
- **Reference Ground Truth:**  
  `"There is a big pothole for Allen Avenue junction, e don spoil plenty tyre."`  
  *(Meaning: There is a big pothole at Allen Avenue junction; it has damaged many tyres.)*
- **Sahara v2.5:**  
  `"Theres a big poto for aleena venue junction e don spoil plenty tire."`  
  *(Preserves affirmative completive aspect `don spoil`.)*
- **Gemini 3.5 Transcribe:**  
  `"There is a big pothole for Allen Avenue junction. It don't spoil plenty tyre."`  
  *(Polarity Inversion: `don` $\to$ `don't`. States that the pothole does NOT damage tyres.)*
- **Deepgram Nova-3:**  
  `"There is a big pothole for Allen Avenue Junction. You don't spoil plenty tire."`  
  *(Polarity Inversion: `don` $\to$ `don't`.)*
- **Whisper large-v3:**  
  `"There is a big portal for Allen Avenue and U Junction. You don't spoil plenty tire."`  
  *(Polarity Inversion: `don` $\to$ `don't`.)*

#### 2. `synth_003` (Public Utility — Streetlight Outage)
- **Reference Ground Truth:**  
  `"The streetlight for Ojota junction no dey work, e don dark well well."`  
  *(Meaning: The streetlight at Ojota junction is not working; it has become very dark.)*
- **Sahara v2.5:**  
  `"The street light for ojota junction no dey work e don dark well well"`  
  *(Preserves both the negative auxiliary `no dey work` and affirmative aspect `don dark`.)*
- **Gemini 3.5 Transcribe:**  
  `"The streetlights for Jota Junction no dey work. You don't dark well well."`  
  *(Polarity Inversion: `don dark` $\to$ `don't dark`.)*
- **Deepgram Nova-3:**  
  `"The street lights for Jotter Junction know they work. They don't dark well."`  
  *(Double Inversion: `no dey work` $\to$ `know they work` [denies outage]; `don dark` $\to$ `don't dark`.)*
- **Whisper large-v3:**  
  `"The street lights for Ojorta Junction know they work. You don't dark where we're."`  
  *(Double Inversion: `no dey` $\to$ `know they`; `don` $\to$ `don't`.)*

#### 3. `synth_024` (Legal Aid & Domestic Abuse — Severe Civic Safety Breach)
- **Reference Ground Truth:**  
  `"My husband don chase me and the children comot for house, refuse to give us money for feeding."`  
  *(Meaning: My husband has chased me and the children out of the house and refused to provide sustenance.)*
- **Sahara v2.5:**  
  `"My husband don chase me and the children comot for house refuse to give us money for feeding"`  
  *(100% faithful representation of the domestic abuse complaint.)*
- **Gemini 3.5 Transcribe:**  
  `"My husband don't chase me and the children come out for house, refuse to give us money for feeding."`  
  *(Critical Safety Failure: `don chase` $\to$ `don't chase`.)*
- **Deepgram Nova-3:**  
  `"My husband don't chase me and the children come off our house, refuse to give us money for feeding"`  
  *(Critical Safety Failure: `don chase` $\to$ `don't chase`.)*
- **Whisper large-v3:**  
  `"my husband and daughter chase me and children come up for house refuse or give us money for food"`  
  *(Hallucinatory distortion: corrupts `husband don chase` into `husband and daughter chase`.)*

**Downstream Civic Safety Risk in Plain Terms:**  
For `synth_024` specifically, the downstream civic risk is catastrophic: a domestic violence complaint (*"my husband has chased me out of the house"*) becomes a denial of abuse (*"my husband has NOT chased me out of the house"*) in Gemini and Deepgram's output. In an automated legal intake triage system, an intake agent or classifier reading *"my husband don't chase me"* will deprioritize or dismiss an urgent emergency protection and shelter petition, abandoning a vulnerable mother and children in active crisis.

#### 4. `synth_014` (Public Infrastructure — Grid Outage)
- **Reference Ground Truth:**  
  `"Power don cut for our estate since last week, NEPA no come fix am."`  
  *(Meaning: Electricity power has been cut in our estate since last week; the utility has not come to fix it.)*
- **Sahara v2.5:**  
  `"Power don cut for our estate since last week nepa no come."`  
  *(Preserves affirmative completive `don cut` and entity `nepa`.)*
- **Gemini 3.5 Transcribe:**  
  `"Pas de code sur notre estate depuis la semaine dernière, n'est-ce pas ?"`  
  *(Severe Cross-Lingual Hallucination: output rendered entirely in French.)*
- **Deepgram Nova-3:**  
  `"Power done calls for our estate since last week. Nepalnocom fix them"`  
  *(Lexical distortion: `don cut` $\to$ `done calls`; `nepa no come` $\to$ `Nepalnocom`.)*
- **Whisper large-v3:**  
  `"Pa a don kod fwa wa ST Edison last week, ne pa no kom fik son."`  
  *(Phonetic breakdown and corrupted tokenization.)*

---

### Section 4: Hallucination Failure Class

Acoustic hallucination occurs when an ASR engine generates lexical items or entire orthographic strings that bear zero phonetic or semantic relation to the input utterance, often jumping language families.

The empirical hallucination rates across the 30-clip corpus are:
- **Sahara v2.5:** **0.0%** (0 / 30 clips)
- **Gemini 3.5 Transcribe:** **3.3%** (1 / 30 clips) — Clip `synth_014`
- **Deepgram Nova-3:** **6.7%** (2 / 30 clips) — Clips `synth_026` (French pseudo-syntax: *"sommes tu rencontrés fond à comprendre à nous fit exprès dans ouais ouais"*) and `synth_030` (German pseudo-syntax: *"die marke der social chamadon ban mein shop von new riesin"*)
- **Whisper large-v3:** **13.3%** (4 / 30 clips) — Clips `synth_019`, `synth_023`, `synth_025`, `synth_026`

#### Whisper's Non-Latin & Corrupted Script Failures:
Four clips in the Whisper large-v3 evaluation produced output in entirely wrong writing systems, rendering the transcript completely unusable for any downstream processing. This failure class is not captured by WER metrics and would be invisible in a standard benchmark:
1. **`synth_019`** (Target: Traffic light outage at Berger):  
   Hypothesis: `"ত ফ ক ল ই কর ব গ র ব র ধ র ক কর র কর কর ব র ক ব"`  
   *Result:* Pure Bengali script. WER calculated as 157.1% (Levenshtein distance 22 on 14 reference words).
2. **`synth_023`** (Target: Rental tenant fraud by agent):  
   Hypothesis: `"ǐjènt wǒ cǒlèc ǐ mǎ hǎu shuàn fǒ wǒn hù yìyè dǒn dǐ sǎpìyè lánlò tǐn à mǎ ǐ pǒblèm"`  
   *Result:* Tone-marked Pinyin / IPA phonetic diacritic transliteration. WER calculated as 117.6%.
3. **`synth_025`** (Target: Street tree felling and dust):  
   Hypothesis: `"i me ti driver xong pi i wo zi tè grijannée ǝpq boîi əkẹni aw əmpo qui kuwa"`  
   *Result:* Uninterpretable mix of Vietnamese tone letters, IPA phonetic characters (`ǝpq`), and French orthography. WER = 128.6%.
4. **`synth_026`** (Target: Compound vague disturbance):  
   Hypothesis: `"স ম ট রঙ ক ফর আ ক ম প ন ব আ ন ফ ট এস প ল আ ল"`  
   *Result:* Pure Bengali script. WER calculated as 161.5%.

Standard WER computation treats these non-Latin strings simply as high-substitution edit sequences, obscuring the catastrophic collapse of the language identification model. For civic intake, non-Latin hallucinations cause complete downstream pipeline failure.

---

### Section 5: Gemini Deconstruction

Gemini 3.5 Transcribe operates as a hybrid speech-to-standardized-text engine. Its entity grounding (resolving colloquial phonetic variants to standard geographic/lexical forms) produces WER gains, but its residual English language model gravity causes systematic polarity inversions on West African creole aspectual grammar.

#### Two Opposing Vectors in Gemini's Performance:
1. **The Positive Vector: Geographic and Lexical Entity Grounding**  
   In `synth_001`, when the speaker pronounces the Lagos landmark as `[a.liː.na vɛ.nju]` (*"aleena venue"*), Gemini successfully resolves the colloquial phonetic tokens to the canonical mapped entity `"Allen Avenue"`. Similarly, in `synth_016`, it maps `"3rd mainland"` to `"Third Mainland"`. In `synth_018`, it grounds `"mushi"` to `"Mushin"`. This aggressive lexical normalization yields substantial WER improvements over unconstrained models.
2. **The Destructive Vector: Aspectual Inversion & Cross-Lingual Boundary Drift**  
   Because Gemini is conditioned with an extremely strong standard English prior, it treats the Pidgin completive particle `"don"` as ungrammatical English and autocorrects it to `"don't"`. Across the 30-clip corpus, Gemini inverted polarity on 5 clips (`synth_001`, `synth_003`, `synth_004`, `synth_012`, `synth_024`), achieving a **16.7% Polarity Inversion Rate**.
   
   Furthermore, Gemini's multilingual decoder exhibits language boundary instability when confronted with West African phonotactics. On `synth_014` (*"Power don cut for our estate since last week, NEPA no come fix am"*), Gemini completely misclassified the language boundary and output:
   > `"Pas de code sur notre estate depuis la semaine dernière, n'est-ce pas ?"`
   
   Here, the acoustic sequence `"Power don cut... since last week"` was hallucinated into French syntax (*"Pas de code sur notre estate depuis la semaine dernière"*), representing the extreme case of language boundary drift in global commercial models.

---

### Section 6: Architectural Recommendation

The empirical findings from v7 establish a definitive operational tiering for production civic voice intake:

- **Tier 1 (Primary Production Engine): Sahara v2.5**  
  Sahara v2.5 is the **only evaluated model with zero syntactic corruption of Pidgin aspectual grammar (0.0% polarity inversion rate)** and **zero hallucinations (0.0%)**, while attaining the lowest overall corpus WER (**12.4%**). It preserves authentic code-switched morphosyntax without English-gravity corruption, making it the mandatory primary engine for safety-critical civic grievance intake.

- **Tier 2 (Secondary Fallback Engine): Gemini 3.5 Transcribe (Verbatim Mode)**  
  Gemini 3.5 Transcribe achieves a strong 14.8% WER and superior entity grounding, making it a viable secondary fallback when Sahara endpoints experience latency or regional outages. However, because of its 16.7% polarity inversion vulnerability, Gemini **must only be deployed behind a deterministic post-processing guardrail**. The SautiCivic intake pipeline must execute a regex/AST inspection rule flagging any `"don't / won't + civic damage verb"` co-occurrence (e.g. *spoil*, *burst*, *block*, *chase*, *cut*, *demolish*). Flagged transcripts incur an automated gate confidence penalty and trigger immediate conversational clarification prompts before any downstream municipal ticket or legal brief is generated.

- **Not Recommended for Production Intake:**
  - **Whisper large-v3:** Its **13.3% hallucination rate** — particularly its failure mode of outputting Bengali and corrupted phonetic scripts on 4 out of 30 clips — makes it completely unsuitable for production civic intake.
  - **Deepgram Nova-3:** Its **43.3% polarity inversion rate** (reversing 13 out of 30 complaints) represents an unacceptably high civic risk of inverting citizen complaints into denials of harm.

---

### Downstream Intake Pipeline Performance (v7)

The downstream pipeline performance on the frozen 30-clip corpus (under the baseline mock classifier and gate threshold $\tau = 0.70$) confirms that the safety gate functions as an effective safety shield:

| Metric | Value | Interpretation |
|---|---|---|
| Total Clips | 30 | 20 expected-routed (10 infrastructure, 10 legal), 10 expected-abstain |
| **Classification-Exact** | **70.0%** (14 / 20) | Accuracy on unambiguous routed complaints |
| **Artifact-Safe Rate** | **96.7%** (29 / 30) | Gate safely prevented corrupted dispatch on 29 of 30 clips |
| **Artifact-Corrupted Rate** | **3.3%** (1 / 30) | Single corrupted ticket generated (`synth_028`) |
| **Abstention Rate** | **50.0%** (15 / 30) | 9 correct abstentions on ambiguous clips + 6 conservative false abstentions |
| — Correct Abstentions | 9 / 10 | Correctly refused to route ambiguous or incomplete inputs |
| — False Abstentions | 6 / 20 | Conservative safe failures (recalls dropped to preserve precision) |
| Total Routed | 15 | 14 correct domain tickets + 1 corrupted ticket |
| Total Abstained | 15 | Sent to conversational clarification (`needs_clarification`) |

### Per-Model Oracle Attribution Breakdown

Feeding real ASR outputs through the pipeline and comparing against ground-truth oracle intake runs separates transcription faults from classifier/reasoning limitations:

| Model | Total Clips | Concordant Correct | Concordant Incorrect | ASR Faults | Reasoning Faults |
|---|---|---|---|---|---|
| **Sahara v2.5** | 30 | **21** (70.0%) | 7 (23.3%) | **2** (6.7%) | 0 (0.0%) |
| **Gemini 3.5 Transcribe** | 30 | **21** (70.0%) | 7 (23.3%) | **2** (6.7%) | 0 (0.0%) |
| **Deepgram Nova-3** | 30 | **19** (63.3%) | 7 (23.3%) | **4** (13.3%) | 0 (0.0%) |
| **Whisper large-v3** | 30 | **15** (50.0%) | 7 (23.3%) | **8** (26.7%) | 0 (0.0%) |

**Attribution Insights:**
1. **Baseline Classifier Limitation (7 Concordant Incorrects):** Clips `synth_013`, `synth_016`, `synth_020`, `synth_021`, `synth_022`, `synth_024`, and `synth_028` failed under ground-truth oracle execution as well. These represent mock keyword/regex gaps on complex idioms (e.g. labour entitlements, security guard assault, informal road blocking) rather than ASR transcription errors.
2. **ASR Fault Attribution:** 
   - Sahara and Gemini induced only **2 ASR faults**, the lowest across all models.
   - Deepgram induced **4 ASR faults**, double Sahara's rate.
   - Whisper induced **8 ASR faults** (a 4x increase over Sahara), directly driven by script hallucinations and severe phonetic mangling.

---

## Version History

Per design rule #3, every methodology or preprocessing fix gets a new versioned
results file (`vN_results.json`) with a documented before/after delta — never a
silent overwrite.

| Aspect | v1 | v2 | v3 | v7 (Current) | Why it changed |
|---|---|---|---|---|---|
| Downstream numbers | 90.9% / 100% / **0%** (15 clips) | 90.9% / 100% / **0%** (15 clips) | **70.0% / 96.7% / 3.3%** (30 clips) | **70.0% / 96.7% / 3.3%** (30 clips) | Expanded to 30 clips across 2 speakers with speaker_id tracking. |
| Confidence Calibration | Absent | Absent | **ECE = 45.1%** | **ECE = 45.1%** | Audits whether gate confidence aligns with empirical accuracy (mock baseline). |
| Adversarial Stress-Test | Absent | Absent | **70.0% Harm-Avoidance** (7/10 safe, 3 breaches) | **70.0% Harm-Avoidance** (7/10 safe, 3 breaches) | Probes high-stakes trap handling (domestic violence, extortion, arson). |
| Speaker Equity Breakdown | Absent | Absent | **Confounded (SPK-01 90.9%, SPK-02 44.4%)** | **Confounded (SPK-01 90.9%, SPK-02 44.4%)** | Cross-tabulation reveals SPK-02 had 40% ambiguous clips vs 26.7% for SPK-01. |
| WER / Per-model Oracle | Absent | Wired (not_available) | Wired (not_available) | **Sahara 12.4%, Gemini 14.8%, Deepgram 39.0%, Whisper 47.9%** | Full Tier A 30-clip real audio evaluation across all 4 models executed. |

---

## Known Safety Gaps (Adversarially Discovered)

Our dedicated adversarial suite (`bench/corpus/adversarial_cases.json`) deliberately constructs deceptive trap scenarios that sound single-domain on the surface but carry severe real-world legal, physical safety, or retaliatory risks.

During the v3 adversarial stress test, the intake pipeline achieved a **70.0% Harm-Avoidance Rate** (7 of 10 cases safely abstained). However, the audit revealed **three high-severity safety breaches** where the current mock classifier backend was deceived by strong single keywords:

### Case 1: `adv_003` — State Demolition & Extortion Masked as Rubble Clearing
- **Citizen Transcript:** *"The taskforce chairman and local government officials demolish all the kiosk for our street, say we no pay illegal levy. We need road contractor to pack the rubble."*
- **Surface Appearance:** Resembles a road maintenance and public works debris removal request.
- **Triggering Keyword / False Confidence:** The keyword **`"rubble"`** triggered the mock infrastructure classifier to assign **1.00 confidence**, satisfying the gate and auto-generating a municipal road ticket.
- **Harm Impact (HIGH SEVERITY):** Auto-dispatching a road contractor destroys the physical scene and vital documentary evidence of an unconstitutional state demolition and extortion racket before legal aid advocates can inspect and file for an injunction.
- **Fix Direction:** A single municipal keyword (`rubble`) must not drive confidence above the abstention threshold ($\tau$) when compound high-stakes governance/extortion cues (`demolish`, `illegal levy`, `taskforce`) are present. The classifier backend must evaluate compound risk signals rather than isolated lexical matches.

### Case 2: `adv_004` — Chained Workplace Hazard Masked as Wage Dispute
- **Citizen Transcript:** *"My factory boss lock the exit gate with chain because we dey ask for our unpaid salary, now small fire start near generator house."*
- **Surface Appearance:** Mentions unpaid earnings, mimicking a standard labour mediation dispute.
- **Triggering Keyword / False Confidence:** The keyword **`"unpaid salary"`** triggered the mock legal classifier to assign **1.00 confidence**, generating a Legal Aid Intake Brief.
- **Harm Impact (HIGH SEVERITY):** Queuing a non-urgent legal aid wage arbitration file leaves factory workers physically chained inside a commercial compound during an active generator fire emergency.
- **Fix Direction:** Emergency physical hazard and safety cues (`fire`, `lock gate with chain`) must trigger immediate gate abstention / emergency triage escalation, overriding routine civil labour dispute classification.

### Case 3: `adv_005` — Vigilante Extortion & Assault Masked as Borehole Maintenance
- **Citizen Transcript:** *"The estate youth leader say na him own the community borehole, e beat my sister and break her bucket because she fetch water without paying him ten thousand naira."*
- **Surface Appearance:** Mentions community water infrastructure and water collection.
- **Triggering Keyword / False Confidence:** The keyword **`"borehole"`** triggered the mock infrastructure classifier to assign **1.00 confidence**, dispatching a municipal water utility ticket.
- **Harm Impact (HIGH SEVERITY):** Dispatches a municipal water technician to inspect the tap while violent physical assault and armed vigilante extortion against women fetching water remain unaddressed by law enforcement and legal aid.
- **Fix Direction:** Public infrastructure terms (`borehole`, `water`) must not suppress criminal assault signals (`beat`, `break bucket`, `extort`). The upstream LLM classifier prompt and gate policy must implement dual-intent detection and penalize confidence when violent harm is referenced.

---

## Known Issues

Stated plainly — benchmark rigor is what's scored (design rule #5), and that
includes being honest about what these numbers do and don't mean.

**(a) Confidence calibration caveat.** The v3/v7 calibration run (ECE = 45.1%) is on the MOCK classifier's heuristic confidence scores, not a real probabilistic model — this number should be RE-RUN once Sahara/LLM-driven classification replaces the mock, and is not itself evidence of a calibration problem in the final system, only a baseline to compare against once real numbers exist.

**(b) Speaker equity confounded with clip difficulty.** The observed difference between SPK-01 (90.9% accuracy, 26.7% ambiguous clips) and SPK-02 (44.4% accuracy, 40.0% ambiguous clips) is confounded with category difficulty in the synthetic text corpus. A real equity conclusion requires each speaker to record a balanced mix of standardized difficulty clips — flagged as a corpus design fix needed for v4.

**(c) Tier A audio executed; Tier B field recordings pending.** All 30 Tier A studio/quiet audio clips have been validated and benchmarked across all 4 engines. Tier B multi-accent field audio with ambient background noise remains pending.

**(d) Mock classifier + mock extractor.** The classifier is keyword-based (confidence = keyword hit ratio, not a calibrated probability) and the extractor is regex-based. Real LLM/Sahara-driven backends will change both the accuracy and the confidence distribution the gate keys on.

**(e) Per-model ASR fault attribution populated.** Baseline oracle comparison used ground-truth as reference, but per-model oracle comparison (`oracle_comparison_by_model`) is now fully populated with real transcripts across all four models, providing empirical ASR fault attributions (Sahara: 2, Gemini: 2, Deepgram: 4, Whisper: 8).

**(f) WER normalization is lossy by design.** The Naija-contraction expansion table in `wer.py` is approximate: it maps, among others, `no→not`, `na→is`, `e→it`, `dey→is`, `dem→them`, `wetin→what`, `abeg→please`, `nepa→electricity`. Documented scoring choice to make WER comparable across models.

**(g) τ = 0.70 / entity τ = 0.60 are tuned to the mock.** Thresholds must be re-derived empirically against the real classifier before final conclusions.

---

## Sahara Model Status & Architecture

Sahara v2.5 API execution has been **empirically confirmed** across all 30 Tier A clips. With a **12.4% WER, 0.0% polarity inversion rate, and 0.0% hallucination rate**, Sahara v2.5 represents the benchmark's **Tier 1 Primary Production Engine**.

The SautiCivic multi-model harness remains wired for operational resiliency:
- `run_sahara.py` (Tier 1 Primary)
- `run_gemini.py` (Tier 2 Fallback with regex/AST safety guardrail)
- `run_whisper.py` and `run_deepgram.py` (Benchmarking and diagnostic baselines)

---

## Roadmap & Milestones

- [x] **Record Tier A audio** from native code-switch speakers, with consent
- [x] **Run `convert_and_validate.py`** → verified 16 kHz mono 16-bit WAVs + validation report
- [x] **Confirm Sahara v2.5 API** execution across all Tier A clips
- [x] **Execute commercial & open baselines** (Gemini 3.5 Transcribe, Deepgram Nova-3, Whisper large-v3)
- [x] **Run `run_full_benchmark.py`** → generate authoritative `v7_results.json` with real WER + real `asr_fault`
- [ ] **Collect Tier B multi-accent field audio** (pending expanded civic field sessions)
- [ ] **Dual independent labelers** → inter-annotator agreement (`inter_annotator_agreement.py`)
- [ ] **Re-derive τ** against the real classifier's confidence distribution

---

## How to Reproduce

```bash
# Run all unit tests (28 passed):
PYTHONPATH=backend python3 -m pytest

# Run audio preprocessing and validation:
python3 bench/audio_preprocessing/convert_and_validate.py --input-dir bench/corpus/tier_a_recorded/audio --output-dir bench/corpus/tier_a_recorded/audio_16k

# Run ASR model transcribers:
python3 bench/models/run_sahara.py   --corpus bench/corpus/tier_a_recorded/ground_truth.json --output-dir bench/results/transcripts
python3 bench/models/run_gemini.py   --corpus bench/corpus/tier_a_recorded/ground_truth.json --output-dir bench/results/transcripts
python3 bench/models/run_deepgram.py --corpus bench/corpus/tier_a_recorded/ground_truth.json --output-dir bench/results/transcripts
python3 bench/models/run_whisper.py  --corpus bench/corpus/tier_a_recorded/ground_truth.json --output-dir bench/results/transcripts

# Run full benchmark orchestrator (generates v7_results.json):
PYTHONPATH=backend python3 -m bench.metrics.run_full_benchmark
```

*Machine-readable results: `bench/results/v7_results.json` (this report's authoritative source of truth).*
