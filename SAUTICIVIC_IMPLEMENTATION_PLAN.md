# SautiCivic Bridge — Phase 2 Implementation Plan (v2)
**Sahara CodeSwitch Africa Challenge — Legal & Public Services Track**
**Build window:** Aug 15 – Sep 15, 2026 (5 weeks)
**Status: Not yet started building — folder structure only. This is the planning doc an agent should follow, in order, once building begins.**

This plan incorporates lessons from Phase 1's winning benchmark (Sauti Ledger) and a technical review that caught a real gap in v1 of this plan (a scored behavior — abstention — with no architectural mechanism to produce it).

---

## 1. What We're Building

One voice intake pipeline, two downstream outcomes: a citizen speaks a code-switched complaint, the system classifies it as either a **municipal infrastructure issue** or a **legal grievance**, extracts relevant entities, and generates the correct structured artifact — a dispatched municipal ticket, or a Legal Aid Intake Brief. **A third outcome — abstain and ask a clarifying question — exists whenever the system isn't confident enough to safely generate either artifact.**

**Headline metric (the actual thing being judged at 30% weight):** did a transcription or reasoning error corrupt the downstream artifact — wrong classification, wrong entity, or worse, silently misfiling something high-stakes (e.g. a domestic-violence grievance as a pothole ticket). "Artifact-corrupted" must be as close to 0% as possible; the abstain gate is the mechanism that makes that achievable rather than aspirational.

---

## 2. Repo Structure

```
sauticivic-bridge/
├── backend/
│   ├── app/
│   │   ├── schemas.py                 # Domain, Entity, ClassificationResult, IntakeOutcome (dataclasses/enums)
│   │   ├── pipeline.py                # run_intake() — extract → classify → GATE → outcome. Single choke point.
│   │   ├── gate.py                    # decide(): confidence/completeness check -> route or abstain-and-ask
│   │   ├── agents/
│   │   │   ├── classifier_agent.py    # infra-vs-legal, pluggable backend (mock now, real LLM/Sahara later)
│   │   │   └── extraction_agent.py    # entities + per-entity confidence, feeds the gate
│   │   ├── routers/
│   │   │   └── intake.py              # thin FastAPI layer over pipeline.run_intake()
│   │   ├── services/
│   │   │   ├── sahara_asr.py
│   │   │   ├── ticket_dispatch.py
│   │   │   └── legal_brief_generator.py
│   │   ├── db/
│   │   │   ├── schema.sql             # complaints, classifications, artifacts, audit_log, gate_decisions
│   │   │   └── session.py
│   │   ├── demo_gate.py
│   │   └── main.py
│   └── tests/
│       └── test_gate.py
├── frontend/                          # demo-ware — see Section 7 scope rule, thin this first if time is tight
│   └── src/
│       ├── components/
│       │   ├── VoiceIntake.jsx        # recording + text-fallback input, built together from day one
│       │   ├── ClassificationView.jsx # shows routing decision + confidence + reasons + clarify state
│       │   ├── TicketCard.jsx
│       │   └── LegalBriefCard.jsx
│       └── pages/
│           └── Dashboard.jsx
├── bench/
│   ├── corpus/
│   │   ├── tier_a_recorded/
│   │   │   ├── audio/
│   │   │   ├── ground_truth_labeler1.json     # first native-speaker labeling
│   │   │   ├── ground_truth_labeler2.json     # second, INDEPENDENT native-speaker labeling
│   │   │   ├── ground_truth_final.json        # reconciled; disagreements kept as "ambiguous" subset
│   │   │   ├── ambiguous_subset.json           # the disagreement cases — doubles as the abstain-gate test set
│   │   │   └── MANIFEST_SHA256.txt
│   │   └── tier_b_public/
│   ├── models/
│   │   ├── run_sahara.py
│   │   ├── run_whisper.py
│   │   └── run_deepgram.py
│   ├── metrics/
│   │   ├── wer.py
│   │   ├── downstream_accuracy.py     # classification-exact / artifact-safe / artifact-corrupted
│   │   ├── run_oracle_comparison.py   # NEW — ASR-transcript run vs. ground-truth run, per clip, attributes every failure
│   │   ├── inter_annotator_agreement.py  # NEW — agreement % / Cohen's kappa between labeler1 and labeler2
│   │   └── run_full_benchmark.py
│   ├── results/
│   │   ├── v1_results.json
│   │   ├── v2_results.json
│   │   ├── v3_results.json
│   │   └── REPORT.md                  # includes a "Known Issues" section — document mock-backend quirks as found, don't hide them
│   └── audio_preprocessing/
│       └── convert_and_validate.py    # A/B check against a reference tool, catch preprocessing bugs before they're blamed on models
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SOLUTION_DESCRIPTION.md
│   ├── BENCHMARK_REPORT.md
│   ├── ETHICS_INCLUSION_NOTE.md
│   └── DATA_CONSENT_LOG.md
├── infra/
│   └── docker-compose.yml
└── README.md
```

---

## 3. System Architecture (corrected — includes the gate node v1 was missing)

```
Citizen voice/text input (Web, text-fallback always available)
   │
   ▼
Sahara v2.5 ASR (streaming, bilingual code-switch aware)
   │  → transcript + language-pair detected
   ▼
Extraction Agent
   │  → entities + PER-ENTITY CONFIDENCE (location, party names, complaint type, urgency cues)
   ▼
Classifier Agent
   │  → domain (infra/legal) + CONFIDENCE SCORE
   ▼
┌─────────────────────────────────────────────────────┐
│  CONFIDENCE / COMPLETENESS GATE  (gate.py::decide()) │
│  Fires abstain-and-ask if:                           │
│    - classifier confidence < τ (default 0.70,        │
│      re-tune once real backend replaces mock), OR    │
│    - a required entity is missing/low-confidence     │
│      (location for a ticket; party names for a brief)│
└─────────────────────────────────────────────────────┘
   │                              │
   ▼ (confident + complete)       ▼ (abstain)
Route to domain-specific       "Needs Clarification" state
artifact generation            → clarifying question surfaced
   │                              to user, no artifact generated
   ▼
Ticket Dispatch / Legal Brief Generator
   │
   ▼
Audit Log (Postgres) — every gate decision + reasons logged, explainable
```

**Key design decisions and tradeoffs:**

1. **The gate is a single choke point (`pipeline.py::run_intake()`), decoupled from the classifier/extractor backend.** Tradeoff: slightly more indirection, but it means the mock classifier can be swapped for the real Sahara/LLM pipeline without touching gate logic — the safety-critical piece stays independently testable regardless of what sits upstream.

2. **Abstention is a first-class outcome, not an error state.** Tradeoff: adds a third branch to test and design UI for, but it's what actually drives "Artifact-corrupted" toward zero — the metric the whole submission is scored on.

3. **Text-input fallback built alongside voice from day one**, not patched in later. Direct lesson from Phase 1's 3am audio-encoding crisis.

---

## 4. Benchmarking Architecture

### 4.1 Corpus — two tiers, two independent labelers
- **Tier A (primary):** 20-30 self-recorded utterances, Nigerian Pidgin/Yoruba/English code-switch, AI-drafted then native-speaker-corrected before recording.
- **Two independent native speakers label ground truth separately** (`ground_truth_labeler1.json`, `ground_truth_labeler2.json`). Report inter-annotator agreement (`inter_annotator_agreement.py` — simple % agreement, Cohen's κ if time allows). **Disagreement cases become `ambiguous_subset.json` — the primary test set for validating the abstain gate actually fires where it should.**
- Freeze the reconciled corpus with a SHA256 manifest before running any model. No clip added or dropped after seeing results.
- **Tier B (secondary):** public code-switching dataset (AfriSwitch or similar), used as-is, cited, not redistributed — covers language pairs Tier A doesn't.

### 4.2 Metrics
| Metric | What it measures |
|---|---|
| WER (normalized + raw) | Baseline ASR accuracy |
| Entity accuracy | Did key entities survive transcription |
| Classification-exact | Correct domain routing survived end-to-end |
| Artifact-safe | Correct artifact generated OR gate correctly abstained |
| **Artifact-corrupted** | Wrong artifact silently generated — the number that must be ~0 |
| **Abstention rate** | How often the gate fires, per model |
| **ASR-fault vs. reasoning-fault** | Via the oracle comparison below — attributes every failure to the right layer |

### 4.3 Oracle-vs-ASR attribution run (`run_oracle_comparison.py`)
For every Tier A clip, run `pipeline.run_intake()` **twice**: once on the model's ASR transcript, once on the ground-truth transcript (the "oracle" run). Classify every mismatch as:
- **ASR-fault** — oracle run was correct, ASR-transcript run wasn't → the transcription error caused the failure
- **reasoning-fault** — oracle run was ALSO wrong → the classifier/extractor/gate itself is the weak point, not ASR
- **concordant-correct** / **concordant-incorrect** (the latter usually signals an ambiguous ground-truth case)

Additionally, correlate abstentions against fault type: of all gate-triggered abstentions, what fraction were warranted (ASR-fault, transcript genuinely was bad) vs. unwarranted (reasoning-fault, the gate fired even on a clean transcript, meaning the threshold/extraction logic needs tuning, not the ASR).

This is the single most rigor-demonstrating piece of the whole benchmark — it directly stops any model from being blamed for a weak prompt, and it turns "we built an abstain gate" into "we can prove when and why it fires correctly."

### 4.4 Preprocessing A/B check
Before trusting any benchmark number, spot-check a sample of converted audio against the same clips run through Sahara's own web UI manually. If they diverge, treat it as a preprocessing bug, not a model weakness — this is exactly the class of bug that nearly derailed AEGIS's benchmark and was the winning team's most credibility-building disclosure.

### 4.5 Compute Environment (updated decision)
**The local dev machine does NOT run audio model inference.** Whisper large-v3 is too large; Sahara/Deepgram are cloud APIs.

| Workload | Where |
|----------|-------|
| Backend server, pytest, text metric scripts | **Local** |
| `run_whisper.py`, `run_sahara.py`, `run_deepgram.py`, `convert_and_validate.py` | **Google Colab / cloud** |

Model scripts write transcript JSONs to `bench/results/transcripts/<model>/` which are committed back to the repo so metric computation can happen locally.

### 4.6 Models benchmarked
Sahara v2.5, Whisper large-v3, Deepgram Nova-3.

### 4.7 Version transparency
Every methodology correction gets a new results file (`v1_results.json`, `v2_results.json`...), preserved, with a documented before/after delta in `REPORT.md`. Never silently overwrite a prior run.

---

## 5. Implementation Timeline (5 weeks)

| Week | Focus | Deliverable |
|---|---|---|
| **1A** (Aug 15-18) | **Track A — Code (you control):** finish wiring `config.py` into pipeline/gate; add `requirements.txt`, `.gitignore`, `pytest.ini`, `.env.example`; create `README.md` with setup/run/test instructions; create real `docker-compose.yml` (backend + Postgres); write `schema.sql` for audit log | `requirements.txt` + `.gitignore` committed; `pytest` runnable; `docker-compose up` starts backend + DB |
| **1B** (Aug 18-21) | **Track B — Corpus (depends on people):** Sahara v2.5 API access confirmed; native speaker recruited; Tier A script drafting + recording begins; if speakers unavailable, draft synthetic test cases to unblock benchmark scripting | Speaker recruitment started; if blocked, synthetic placeholder corpus documented as such |
| **2** (Aug 22-28) | Real Sahara integration replaces mock ASR; text-input fallback built alongside; ticket dispatch + legal brief generation wired | End-to-end pipeline working on real transcripts for at least one model; `POST /intake/{session_id}/clarify` endpoint wired; `config.py` driving all thresholds (no hardcoded values in gate.py) |
| **3** (Aug 29-Sep 4) | Whisper + Deepgram integrated; inter-annotator agreement computed; ambiguous subset finalized; audit log/explainability view | All 3 models producing transcripts on the full corpus |
| **4** (Sep 5-11) | Full benchmark run: WER, downstream accuracy, **oracle comparison**, abstention correlation; preprocessing A/B check; iterate and version (v1→v2→v3) | `bench/results/REPORT.md` complete with fault attribution and version history |
| **5** (Sep 12-15) | Demo video, submission docs, final self-audit against all 5 criteria. **If time is short, thin the frontend, not the benchmark work (Section 7 rule).** | Full submission package |

---

## 6. Ethics
`docs/DATA_CONSENT_LOG.md` tracks consent for every real speaker recorded in Tier A — required from week 1, not retrofitted, since this project (unlike Phase 1's AEGIS) uses real human voices.

---

## 7. Standing Scope Rule (decided now, not renegotiated under pressure later)
**The benchmark is what's scored; the frontend is demo-ware.** If weeks 4-5 get tight, thin `Dashboard.jsx`/card components to the minimum the demo video needs, and spend the reclaimed hours on corpus quality, labeler agreement, and error analysis instead. This is a standing team agreement, not a decision to be made in the moment.

---

## 8. Checklist — "doing it right," restated
- [ ] Real, native-speaker-validated recorded corpus
- [ ] TWO independent labelers, agreement reported, disagreements kept as a documented ambiguous subset
- [ ] Frozen corpus hash before any model is run
- [ ] Confidence/completeness gate as a real architectural node, not just a scored aspiration
- [ ] Oracle-vs-ASR run attributing every failure to the correct layer
- [ ] Abstention rate correlated against fault type
- [ ] Audio preprocessing A/B-checked against a reference tool
- [ ] Every methodology correction versioned and disclosed
- [ ] Text-input fallback built from day one
- [ ] Consent log for every real recorded speaker
- [ ] Frontend explicitly deprioritized under time pressure, per Section 7
- [ ] `requirements.txt` / dependency management committed
- [ ] `.gitignore` prevents `__pycache__`, `.env`, audio files from polluting repo
- [ ] `config.py` drives all thresholds — no magic numbers in source
- [ ] `README.md` has setup + run + test instructions
- [ ] `docker-compose.yml` starts backend + Postgres
- [ ] Demo video script finalized before recording
- [ ] Sahara contingency plan activated if API access not confirmed by end of Week 1

## 9. Sahara Contingency Plan
If Sahara v2.5 API access is not confirmed by end of Week 1:
- Proceed with Whisper large-v3 as primary ASR for pipeline development and initial benchmarking
- The pluggable architecture (`sahara_asr.py` is a service behind the pipeline, not embedded in it) means Sahara can be integrated when available without reworking the pipeline or gate
- Document the substitution transparently in `REPORT.md` — judges value honesty about constraints more than a claim of using the sponsored tool that can't be substantiated

## 10. Demo Video Plan
- **Duration:** 3–5 minutes
- **Tool:** OBS Studio or Loom
- **Script outline:**
  1. (30s) Problem statement — who this serves and why existing tools fail them
  2. (60s) Live demo: voice input of a clear infrastructure complaint → transcription → classification → ticket generated
  3. (60s) Live demo: voice input of an ambiguous complaint → gate abstains → clarifying question → user answers → correct routing
  4. (30s) Live demo: text fallback input showing the same pipeline works without audio
  5. (30s) Benchmark results highlight — artifact-corrupted rate, oracle comparison, abstention correlation
  6. (30s) Architecture diagram walkthrough — gate as safety mechanism
- **Record by:** Sep 13 (2 days before deadline for editing buffer)
