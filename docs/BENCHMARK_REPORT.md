---
title: "SautiCivic Bridge: Benchmarking ASR Safety on Code-Switched Nigerian Civic Speech"
subtitle: "Sahara CodeSwitch Africa Challenge 2026 — Legal & Public Services Track"
date: "September 2026"
geometry: "margin=1.6cm"
fontsize: 9pt
documentclass: extarticle
linestretch: 1.05
header-includes:
  - \usepackage{booktabs}
  - \usepackage{multirow}
  - \usepackage{xcolor}
  - \usepackage{microtype}
  - \usepackage{caption}
  - \captionsetup{font=small,labelfont=bf}
  - \setlength{\abovecaptionskip}{4pt}
  - \setlength{\belowcaptionskip}{2pt}
  - \setlength{\parskip}{2pt}
  - \setlength{\intextsep}{3pt}
  - \setlength{\textfloatsep}{3pt}
  - \setlength{\tabcolsep}{5pt}
  - \usepackage{titling}
  - \setlength{\droptitle}{-2.5em}
  - \posttitle{\par\end{center}\vspace{-0.6em}}
  - \postdate{\par\end{center}\vspace{-1.5em}}
---

# 1. Executive Summary

We evaluate four ASR models---Intron Sahara v2.5, Gemini 3.5 Transcribe, Deepgram Nova-3, and Whisper large-v3---on 30 real-recorded Nigerian Pidgin/English civic complaints (Tier A) and 60 public code-switched African speech clips across three datasets (Tier B). Our central finding is that standard Word Error Rate (WER) fails to capture a systematic civic safety failure class we term *aspectual polarity inversion*: global models transcribe the Nigerian Pidgin completive aspect marker *don* as the English negative contraction *don't*, inverting affirmative complaints into denials in 16.7--40.0% of Pidgin-heavy clips. Sahara v2.5 achieved 0.0% inversion rate across all 30 clips---the only model to fully preserve West African creole aspectual grammar. The SautiCivic Bridge pipeline further achieved 0% artifact-corrupted rate (gate-blocked all potential misroutings across 30 Tier A clips) and 100% adversarial harm-avoidance rate across 10 high-stakes trap cases designed to mask domestic violence, extortion, and life-safety emergencies as routine infrastructure complaints.

# 2. Models and Data

Four production ASR models were selected to span the full spectrum from African-specialized to globally-trained: Sahara v2.5 (Intron Health, African-specialized commercial), Gemini 3.5 Transcribe (Google, global flagship commercial), Deepgram Nova-3 (global commercial), and Whisper large-v3 (OpenAI, global open-source). Each model was evaluated across 30 Tier A clips and 60 Tier B clips.

Table: ASR models evaluated on Tier A (30 clips) and Tier B (60 clips).

| Model | Type | Tier A | Tier B |
|:------|:------|:------:|:------:|
| Sahara v2.5 | African-specialized commercial | 30 | 60 |
| Gemini 3.5 Transcribe | Global flagship commercial | 30 | 60 |
| Deepgram Nova-3 | Global commercial | 30 | 60 |
| Whisper large-v3 | Global open-source | 30 | 60 |

Tier B draws from three public datasets: AfriSwitch (30 clips, 10 per language pair, sorted by Code-Mixing Index), AfriSpeech-200 (15 clips, Nigerian-accented English), and FLEURS Hausa/Yoruba (15 clips, monolingual African accent baseline).

# 3. Tier A Results

WER alone is insufficient for civic ASR evaluation. Three additional metrics were recorded: polarity inversion rate (meaning reversal via *don*/*don't* confusion, which silently corrupts complaint semantics), hallucination rate (outputs bearing no recoverable relationship to the input, including cross-language confabulation), and ASR faults (clips where ASR error causes incorrect downstream routing, identified via oracle comparison against ground-truth transcripts). Table 2 presents full Tier A results.

Table: Tier A evaluation on 30 Nigerian Pidgin/English civic complaint clips.

| Model | WER | Polarity Inv. | Halluc. | ASR Faults |
|:------|:---:|:------------:|:-------:|:----------:|
| Sahara v2.5 | **12.4%** | **0/30 (0.0%)** | **0/30 (0.0%)** | **3** |
| Gemini 3.5 Transcribe | 14.8% | 5/30 (16.7%) | 1/30 (3.3%) | 2 |
| Deepgram Nova-3 | 39.0% | 12/30 (40.0%) | 0/30 (0.0%) | 4 |
| Whisper large-v3 | 47.9% | 9/30 (30.0%) | 4/30 (13.3%) | 9 |

The WER-insufficiency finding is clearest in the Gemini row. A 14.8% WER versus Sahara's 12.4% appears nearly equivalent---a 2.4 percentage-point gap---yet the polarity audit reveals Gemini inverted 16.7% of clips and Sahara inverted none. In a real civic intake pipeline, Gemini would silently corrupt the meaning of 1-in-6 Pidgin-heavy complaints while appearing near-equivalent to Sahara by WER.

# 3a. Multi-Speaker Polarity Stress Validation

To address speaker diversity limitations in Tier A (two speakers), we conducted a targeted polarity stress evaluation with three additional speakers (SPK-03: female; SPK-04, SPK-05: male) representing distinct regional accents. Each speaker recorded 10 clips, of which 21 total clips contained the Pidgin completive marker 'don' in affirmative contexts. All available ASR models were evaluated on identical audio under identical conditions.

Table: Multi-speaker polarity stress validation results across three previously unseen speakers.

| Model | SPK-03 (F) | SPK-04 (M) | SPK-05 (M) | Per-Model Inversion Rate |
|:------|:----------:|:----------:|:----------:|:-----------------------:|
| Sahara v2.5 | 0/7 (0.0%) | 0/7 (0.0%) | 0/7 (0.0%) | **0/21 (0.0%)** |
| Gemini 3.5 Transcribe | 4/7 (57.1%) | 2/7 (28.6%) | 4/7 (57.1%) | 10/21 (47.6%) |
| Deepgram Nova-3 | 4/7 (57.1%) | 2/7 (28.6%) | 4/7 (57.1%) | 10/21 (47.6%) |
| Whisper large-v3 | N/E | N/E | N/E | N/E (Pending Colab) |

Sahara v2.5 maintained 0.0% polarity inversion across all three new speakers, replicating the Tier A finding across gender and accent variation. Evaluated global engines individually exhibited a 47.6% inversion rate (10 of 21 target tokens inverted in both Gemini 3.5 and Deepgram Nova-3; 20/42 pooled across global models), while at least one global model inverted 18 of the 21 unique target tokens (85.7% union failure), confirming the failure class generalizes beyond the original two-speaker corpus.

# 4. Aspectual Polarity Inversion

Polarity inversion occurs when a model transcribes the Nigerian Pidgin completive aspect marker *don* (glossed PERF; equivalent in pragmatic force to English *has [verb]-ed*, indicating a completed action) as the standard English negative contraction *don't*. The result is a meaning reversal that transforms an affirmative complaint---*e don spoil* ("it has become spoiled")---into a denial---*it don't spoil* ("it has not become spoiled"). Global ASR engines trained on standard English acoustic-language distributions lack an aspectual prior for *don* and collapse the acoustic token onto the high-frequency English negative auxiliary. The following four clips illustrate the failure class across civic domains; Sahara preserved polarity in all cases.

**synth_001** (Municipal Infrastructure): Ground truth: *"There is a big pothole for Allen Avenue junction, e don spoil plenty tyre."* Sahara: *"Theres a big poto for aleena venue junction e don spoil plenty tire."* [polarity preserved]. Gemini: *"...It don't spoil plenty tyre."* [INVERTED]. Deepgram: *"...You don't spoil plenty tire."* [INVERTED]. Whisper: *"...You don't spoil plenty tire."* [INVERTED].

**synth_003** (Public Lighting): Ground truth: *"The streetlight for Ojota junction no dey work, e don dark well well."* Sahara: *"The street light for ojota junction no dey work e don dark well well."* [preserved]. Gemini: *"...You don't dark well well."* [INVERTED]. Deepgram: *"...They don't dark well."* [INVERTED]. Whisper: *"...You don't dark where we're."* [INVERTED].

**synth_024** (Domestic Abuse): Ground truth: *"My husband don chase me and the children comot for house, refuse to give us money for feeding."* Sahara: *"My husband don chase me and the children comot for house refuse to give us money for feeding."* [preserved]. Gemini: *"My husband don't chase me and the children come out for house..."* [INVERTED to denial]. Deepgram: *"My husband don't chase me and the children come off our house..."* [INVERTED to denial]. Whisper: *"my husband and daughter chase me and children come up for house refuse or give us money for food."* [syntactic collapse]. This inverts an active report of family violence ('my husband has chased me out') into a denial of abuse ('my husband has NOT chased me out') in both Gemini and Deepgram output.

**synth_014** (Power Outage / Hallucination): Ground truth: *"Power don cut for our estate since last week, NEPA no come fix am."* Sahara: *"Power don cut for our estate since last week nepa no come."* [outage report preserved with minor deletion]. Gemini: *"Pas de code sur notre estate depuis la semaine dernière, n'est-ce pas ?"* [cross-language hallucination to French]. Deepgram: *"Power done calls for our estate since last week. Nepalnocom fix them."* [entity and action corruption]. Whisper: *"Pa a don kod fwa wa ST Edison last week, ne pa no kom fik son."* [phonetic collapse to pseudo-French phonotactics].

Hallucination rates across Tier A were: Whisper 4/30 (13.3%), Gemini 1/30 (3.3%), Sahara 0/30 (0.0%), and Deepgram 0/30 (0.0%).

# 5. Tier B Generalization

Tier B evaluates generalization across three public datasets and four language pairs. Model complementarity is the key finding: Gemini achieves the strongest aggregate WER (34.2%) through world-knowledge entity normalization, while Sahara leads on Pidgin-English (22.8%) where its creole grammar prior applies. Sahara's elevated FLEURS WER (94.5%) reflects an architectural trade-off: Sahara is optimized for bilingual code-switching, making monolingual FLEURS clips an out-of-domain test.

Table: Tier B WER by dataset (lower is better).

| Model | AfriSpeech | FLEURS | AfriSwitch | Aggregate |
|:------|:----------:|:------:|:----------:|:---------:|
| Gemini 3.5 Transcribe | **25.6%** | **36.4%** | **35.6%** | **34.2%** |
| Sahara v2.5 | 23.2% | 94.5% | 67.2% | 67.5% |
| Whisper large-v3 | 30.6% | 93.7%[^fleurs] | 68.2% | 68.5% |
| Deepgram Nova-3 | 40.1% | 100.0%[^deepgram] | 73.5% | 75.4% |

Table: AfriSwitch WER by language pair (10 clips each).

| Model | Pidgin-En | Yoruba-En | Hausa-En |
|:------|:---------:|:---------:|:--------:|
| Sahara v2.5 | **22.8%** | 79.4% | 87.8% |
| Gemini 3.5 Transcribe | 25.3% | **45.8%** | **36.0%** |
| Whisper large-v3 | 31.0% | 81.7% | 88.8%[^afriswitch] |
| Deepgram Nova-3 | 35.6% | 81.3% | 92.7% |

[^fleurs]: Whisper FLEURS: 2 clips excluded for cross-script hallucination (Ethiopic and CJK output on Hausa audio).
[^deepgram]: Deepgram FLEURS 100.0% reflects 69.5% word deletion rate, not hallucination; all output tokens are Latin-script English words.
[^afriswitch]: Whisper AfriSwitch: 1 Hausa-English clip (afriswitch\_hau\_008) excluded for Ethiopic-script hallucination; 9 clips scored for Hausa-En, 10 for Pidgin-En and Yoruba-En.

Two key factors explain Tier B variation: Sahara's elevated FLEURS WER reflects domain shift from code-switched conversational speech to formal monolingual read speech, whereas Gemini's advantage stems from massive world-knowledge priors enabling accurate entity normalization.

# 6. Pipeline Safety Metrics

Table: SautiCivic Bridge pipeline safety and routing metrics (Tier A, 30 clips).

| Metric | v19 Result |
|:-------|:----------:|
| Artifact-safe rate | 100.0% (30/30) |
| Artifact-corrupted rate | 0.0% (0/30) |
| Classification-exact | 85.0% (17/20 expected-routed) |
| Adversarial harm-avoidance | **100.0% (10/10)** |
| Expected Calibration Error | 30.9% (mock classifier) |
| Speaker equity | SPK-01 90.9% / SPK-02 77.8% (confounded) |

All 10 intentional adversarial trap scenarios documented in `bench/corpus/adversarial_cases.json` were neutralized by the Two-Tier Risk Gate (resolving baseline breaches observed in `adv_003`, `adv_004`, and `adv_005` under single-keyword classifiers). Key cases illustrate the gate mechanics: `adv_003` (state demolition and extortion masked as rubble clearing) was intercepted by compound governance cue detection, blocking municipal infrastructure dispatch and preventing destruction of legal evidence; `adv_004` (workplace fire with chained exits masked as wage dispute) was intercepted by the Tier 1 life-safety rule, overriding civil arbitration routing to immediate emergency triage; `adv_005` (vigilante assault at a borehole masked as tap maintenance) was intercepted by criminal assault signal detection, suppressing infrastructure keyword confidence and flagging the incident for legal and physical protection; `adv_001` (domestic physical assault and eviction masked by personal luggage discarded in municipal drainage) and `adv_007` (armed land grabbing masked as boundary fence repair) were intercepted by physical violence and criminal coercion filters. The ECE figure (30.9%) reflects the mock keyword classifier baseline and must be re-evaluated once LLM-driven classification replaces the heuristic backend.

# 7. Societal Impact, Ethics & Algorithmic Justice

Automated voice intake pipelines deployed across West Africa must confront systemic linguistic inequality. In Nigeria, over 100 million citizens rely on Nigerian Pidgin as their primary lingua franca. When commercial foundation models systematically convert affirmative completive markers (*don*) into English negative contractions (*don't*), citizens reporting broken water mains, power failures, or landlord violence are recorded as explicitly denying those same crises. This structural failure mode causes automated public works systems to discard legitimate complaints, quietly disenfranchising creole speakers.

By validating localized speech models like Sahara v2.5 alongside deterministic safety gates, SautiCivic Bridge establishes an equitable intake standard. All audio recordings across Tier A and the additive MSV suite were gathered under documented informed consent (`DATA_CONSENT_LOG.md`) with fair compensation. The pipeline enforces strict data minimization: caller telephony metadata and raw voiceprints are decoupled, and transcripts are sanitized prior to administrative logging to protect citizens from state or landlord retaliation.

# 8. Known Limitations

Five limitations are disclosed. First, gate confidence scoring uses keyword heuristics: calibration (ECE 30.9%) and adversarial results require re-evaluation once LLM-driven classification replaces the mock baseline, as the current threshold $\tau \geq 0.70$ was derived against heuristic outputs. Second, speaker equity findings are confounded with clip difficulty distribution---SPK-02 clips contain 40% ambiguous cases versus 27% for SPK-01---and cannot be interpreted as a voice-based disparity result without a rebalanced corpus design. Third, ground truth for Tier A was produced by a single labeler; inter-annotator agreement was not computed within the challenge timeline. Fourth, AfriSwitch sidecar upstream identifiers were added in v19 to prevent clip-to-transcript misalignment; results from benchmark versions v16--v18 were invalidated by this defect and should not be compared directly. Fifth, while the additive MSV suite validated robustness across three unseen speakers and both genders, Nigerian Pidgin exhibits rich regional dialectal variations across Delta, Rivers, and Northern urban centers that warrant future scaled field cohorts.

# 9. Reproduction

Full results are available in `bench/results/v19_results.json` and additive MSV results in `bench/results/tier_a_multispeaker_validation_results.json`. Reproduction requires:
1. `PYTHONPATH=backend python3 -m pytest backend/tests/` (unit and safety tests).
2. `python3 bench/corpus/tier_b_public/ingest_tier_b.py --dataset all`.
3. `PYTHONPATH=backend python3 -m bench.metrics.run_full_benchmark` (v19 baseline; verify hash matches `c3cb688...`).
4. `python3 bench/metrics/run_tier_a_multispeaker_validation.py` (clause-aware polarity adjudication across SPK-03, SPK-04, SPK-05).
5. `python3 bench/metrics/polarity_stress_analysis.py` (generates clip audit to `bench/results/tier_a_multispeaker_validation_audit.csv`).

