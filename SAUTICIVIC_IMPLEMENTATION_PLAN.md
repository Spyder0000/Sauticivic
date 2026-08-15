# SautiCivic Bridge — Phase 2 Implementation Plan
**Sahara CodeSwitch Africa Challenge — Legal & Public Services Track**
**Build window:** Aug 15 – Sep 15, 2026 (5 weeks)

This plan is written with Phase 1's actual winning benchmark (Sauti Ledger) as the explicit bar to clear, not just a reference. Every methodology decision below states which Phase 1 lesson it's addressing.

---

## 1. What We're Building

One voice intake pipeline, two downstream outcomes: a citizen speaks a code-switched complaint, the system classifies it as either a **municipal infrastructure issue** or a **legal grievance**, extracts the relevant entities, and generates the correct structured artifact — a dispatched municipal ticket, or a Legal Aid Intake Brief.

**Core lesson applied from Phase 1:** Sauti Ledger won by measuring whether transcription errors actually corrupted the downstream task (a ledger entry), not just raw WER. Our equivalent: does a transcription error change the *classification* (infrastructure vs. legal) or corrupt an *extracted entity* (location, party name, urgency level) badly enough that the wrong artifact gets generated or dispatched to the wrong place. That's our headline metric, not WER alone.

---

## 2. Repo Structure

```
sauticivic-bridge/
├── backend/
│   └── app/
│       ├── routers/
│       │   ├── intake.py              # POST /intake — voice/text entry point
│       │   └── artifacts.py           # GET endpoints for generated tickets/briefs
│       ├── agents/
│       │   ├── classifier_agent.py    # infrastructure vs. legal routing decision
│       │   ├── urgency_agent.py       # severity/urgency scoring (reused pattern from AEGIS Trust Score)
│       │   └── extraction_agent.py    # entity extraction (location, party names, complaint type)
│       ├── services/
│       │   ├── sahara_asr.py          # Sahara v2.5 streaming client
│       │   ├── ticket_dispatch.py     # mock municipal ticket API (ServiceNow/Jira-style)
│       │   └── legal_brief_generator.py  # structured Legal Aid Intake Brief (PDF/doc)
│       ├── db/
│       │   ├── schema.sql             # complaints, classifications, artifacts, audit_log tables
│       │   └── session.py
│       └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── VoiceIntake.jsx        # recording + text-fallback input (lesson: always have a non-audio fallback)
│       │   ├── ClassificationView.jsx # shows routing decision + confidence + reasons
│       │   ├── TicketCard.jsx         # municipal ticket artifact display
│       │   └── LegalBriefCard.jsx     # legal intake brief artifact display
│       └── pages/
│           └── Dashboard.jsx
├── bench/                              # <-- the entire section 4 lives here, modeled directly on the winning report's structure
│   ├── corpus/
│   │   ├── tier_a_recorded/           # OUR OWN recorded, native-speaker-validated corpus
│   │   │   ├── audio/
│   │   │   ├── ground_truth.json      # verbatim transcript + expected classification/entity parse per clip
│   │   │   └── MANIFEST_SHA256.txt    # corpus frozen before first run — non-negotiable, see section 4
│   │   └── tier_b_public/             # borrowed public dataset (AfriSwitch or similar), used as-is, cited, not redistributed
│   ├── models/
│   │   ├── run_sahara.py
│   │   ├── run_whisper.py
│   │   └── run_deepgram.py
│   ├── metrics/
│   │   ├── wer.py                     # standard WER, normalized + raw
│   │   ├── downstream_accuracy.py     # THE key metric: classification-exact / entity-safe / entity-corrupted
│   │   └── run_full_benchmark.py      # orchestrates all models x all tiers, outputs REPORT.md
│   ├── results/
│   │   ├── v1_results.json            # every scoring version preserved, not overwritten — lesson from Sauti Ledger's v1→v2→v3 transparency
│   │   ├── v2_results.json
│   │   ├── v3_results.json
│   │   └── REPORT.md                  # full report with per-clip transcripts
│   └── audio_preprocessing/
│       └── convert_and_validate.py    # includes an A/B sanity check against a reference tool — lesson: this is exactly where Sauti Ledger caught their resampler bug
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BENCHMARK_REPORT.md            # submission-facing, condensed from bench/results/REPORT.md
│   ├── SOLUTION_DESCRIPTION.md
│   ├── ETHICS_INCLUSION_NOTE.md
│   └── DATA_CONSENT_LOG.md            # new — tracks consent for every recorded speaker, see section 6
├── infra/
│   └── docker-compose.yml
└── README.md
```

---

## 3. System Architecture

```
Citizen voice/text input (Web or WhatsApp-style interface)
   │
   ▼
Sahara v2.5 ASR (streaming, bilingual code-switch aware)
   │  → transcript + language-pair detected
   ▼
Entity Extraction Agent
   │  → location/landmark, party names, complaint description, urgency cues
   ▼
Classifier Agent  ──────────────┐
   │                            │
   ▼ (infrastructure)           ▼ (legal grievance)
Urgency Agent                Legal Domain Classifier
   │ (severity: low/med/high)   │ (tenancy/labor/police conduct/etc.)
   ▼                            ▼
Ticket Dispatch Service      Legal Brief Generator
   │ (mock municipal API,      │ (structured Pre-Action
   │  tracking ID generated)   │  Notice / Intake Brief)
   │                            │
   └──────────► Audit Log (Postgres) ◄──────────┘
              (every classification decision + reasons logged,
               explainable — same pattern as AEGIS's Trust Ledger)
```

**Key design decisions, and their tradeoffs (matches the "technical overview" section format the form will ask for):**

1. **Single shared pipeline with a branching classifier, not two separate apps.** Tradeoff: slightly more complex routing logic upfront, but avoids duplicating the ASR/extraction layer twice — and demonstrates architectural range to judges without doubling build time.

2. **Text-input fallback always available alongside voice.** Direct lesson from AEGIS Phase 1: browser audio encoding (webm/opus) vs. Sahara's PCM expectation caused real last-minute pain. This time, build the conversion/validation step *and* the fallback from day one, not as a 3am patch.

3. **Own recorded corpus as the primary benchmark tier, public dataset as secondary.** Direct lesson from the winning report: their Tier A (self-recorded, native-speaker-corrected) was what produced their most credible, specific findings. A borrowed dataset alone (our Phase 1 approach) reads as thinner.

---

## 4. Benchmarking Architecture — built to match or exceed the winning methodology

This is the section to take most seriously, since Code-Switching Benchmark Quality is the highest-weighted criterion.

### 4.1 Corpus strategy (two tiers, same structure as the winner)

**Tier A — Our own recorded corpus (primary, most credible)**
- Record 20-30 short complaint utterances (both infrastructure and legal scenarios), in Nigerian Pidgin/Yoruba/English code-switch
- **Draft with AI assistance, then have an actual native speaker correct every utterance before recording** — this is non-negotiable, it's the exact step that made Sauti Ledger's corpus credible instead of guessed-at
- Record with a real phone/mic, not synthesized TTS
- Write the expected ground-truth parse for each clip: expected classification (infra/legal), expected entities, expected urgency level
- **Freeze the corpus with a SHA256 manifest hash before running any model.** Document the hash in the report. This single move preempts any "did you cherry-pick results" question.

**Tier B — Public dataset (secondary, for scale and diversity)**
- Pull from AfriSwitch or a similar HuggingFace code-switching collection, used exactly as published, cited, not redistributed
- Covers language pairs Tier A doesn't (aim for at least one pair beyond Pidgin/Yoruba — Hausa or Swahili if available)

### 4.2 The audio preprocessing lesson — build the A/B check in from day one
Sauti Ledger's most impressive disclosure was catching their own resampler bug via an A/B against the vendor's web UI. We should build this check as a standard step, not discover we need it mid-crisis:
```
bench/audio_preprocessing/convert_and_validate.py:
  - Converts raw recordings to Sahara's expected format
  - For a random sample of clips, runs the SAME clip through Sahara's own 
    web UI manually and compares against our pipeline's output
  - If they diverge meaningfully, treat that as a preprocessing bug, not a 
    model weakness, and fix before scoring anything
```

### 4.3 Metrics — WER is necessary but not sufficient (the core Phase 1 lesson)

| Metric | What it measures | Why it's here |
|---|---|---|
| WER (normalized + raw) | Standard ASR accuracy | Baseline, expected by the form |
| Entity accuracy | Did location/party-name/complaint-type survive transcription | Precursor to downstream accuracy |
| **Classification-exact** | Did the correct infra-vs-legal routing decision survive | **This is our version of Sauti Ledger's "transaction-exact"** |
| **Artifact-safe** | Correct artifact generated, OR system asked a clarifying question instead of guessing | Mirrors their "amount-safe" — asking is safe |
| **Artifact-corrupted** | Wrong artifact silently generated/dispatched | The number that must be ~0 — this is the metric that actually matters for real-world deployment |

### 4.4 Models benchmarked
Sahara v2.5, Whisper large-v3, Deepgram Nova-3 — three real, distinct model types (African-specialized commercial, global open-source, global commercial), giving a cleaner three-way contrast than reusing Whisper twice like our Phase 1 attempt.

### 4.5 Version transparency — don't hide iteration, publish it
Every methodology fix (preprocessing bug, classifier threshold tuning, entity-extraction rule change) gets a new results version (`v1_results.json`, `v2_results.json`...) preserved in the repo, with a documented before/after delta in `REPORT.md`. This directly copies the single most credibility-building thing in the winning report.

---

## 5. Implementation Timeline (5 weeks)

| Week | Focus | Deliverable |
|---|---|---|
| 1 (Aug 15-21) | Corpus recording + native-speaker correction; core pipeline scaffolding (reuse AEGIS's FastAPI/React skeleton) | Frozen Tier A corpus with SHA256 manifest; basic intake → transcript flow working |
| 2 (Aug 22-28) | Classifier + extraction agents; Sahara integration; text-input fallback | End-to-end pipeline: voice/text in → classification out, both branches |
| 3 (Aug 29-Sep 4) | Ticket dispatch + legal brief generation; audit log/explainability view | Both downstream artifacts generating correctly; frontend wired |
| 4 (Sep 5-11) | Full benchmark run (all 3 models × both tiers); preprocessing A/B check; bug-fix iteration loop, versioned | `bench/results/REPORT.md` complete with v1→v2→v3 transparency |
| 5 (Sep 12-15) | Demo video, submission docs, final self-audit against all 5 judging criteria, buffer for the inevitable last-minute issue | Full submission package |

---

## 6. Ethics — one addition beyond Phase 1
`docs/DATA_CONSENT_LOG.md` — a simple record of who recorded Tier A audio and confirming their consent for it to be used in this benchmark/demo. Phase 1's AEGIS had no real recorded voices to worry about (synthetic data only); this project does, since Tier A requires real human speakers. This needs to exist from day one, not retrofitted.

---

## 7. What "doing it right" means concretely, restated
Every item below is something Phase 1 either lacked or built under emergency time pressure — this time, build it as a first-class part of the plan, not a patch:
- [ ] Real, native-speaker-validated recorded corpus (not just a borrowed dataset)
- [ ] Frozen corpus hash before any model is run
- [ ] Downstream-task accuracy as the headline metric, not WER alone
- [ ] Audio preprocessing A/B-checked against a reference tool before trusting any result
- [ ] Every methodology correction versioned and disclosed, not silently overwritten
- [ ] Text-input fallback built from day one, not discovered as a 3am necessity
- [ ] Consent log for any real recorded speaker
- [ ] 3-page submission report structure planned from the start, not retrofitted under a page-limit crunch
