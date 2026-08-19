# SautiCivic Bridge - Team Task Split (REVISED)
**Sahara CodeSwitch Africa Challenge | Aug 15 - Sep 15, 2026**
**Team:** drizzy765 / Agoro Timilehin (Lead), David Akhuabe

> Note: drizzy765 and Agoro Timilehin are the same person. Tasks previously split across both are now consolidated under one role.

> **Compute rule (non-negotiable):** Local machine runs backend server, pytest, and text-only metric scripts only.
> All audio model inference — Whisper large-v3, Sahara corpus runner, Deepgram, audio preprocessing — runs on **Google Colab or cloud**. Model runners write transcript JSONs to `bench/results/transcripts/<model>/` and results are committed back.

---

## drizzy765 / Agoro Timilehin - Group Lead
### Benchmarking + Full Backend Pipeline + Architecture
**28 issues** - all the scored, high-stakes, and infrastructure work.

| # | Title | Week | Priority |
|---|-------|------|----------|
| 1 | Corpus setup: Tier A recording + dual-labeler ground truth | Week 1 | [CRITICAL] |
| 2 | `wer.py`, `downstream_accuracy.py`, `inter_annotator_agreement.py` | Week 2-3 | [CRITICAL] |
| 3 | `run_oracle_comparison.py` - ASR-fault vs. reasoning-fault attribution | Week 3-4 | [CRITICAL] |
| 4 | Full benchmark run: WER + downstream + oracle + abstention correlation | Week 4 | [CRITICAL] |
| 5 | Audio preprocessing A/B check (`convert_and_validate.py`) | Week 3 | [HIGH] |
| 6 | Benchmark versioning: v1-v3 results + `REPORT.md` with delta docs | Week 4 | [CRITICAL] |
| 7 | `run_full_benchmark.py` - orchestrates all metric scripts | Week 4 | [CRITICAL] |
| 8 | SHA256 corpus freeze (`MANIFEST_SHA256.txt`) before first model run | Week 2 | [HIGH] |
| 9 | Integrate Whisper large-v3 (`run_whisper.py`) | Week 3 | [HIGH] |
| 10 | Integrate Deepgram Nova-3 (`run_deepgram.py`) | Week 3 | [HIGH] |
| 11 | `gate.py::decide()` - confidence/completeness gate logic | Week 1 | [CRITICAL] |
| 12 | `pipeline.py::run_intake()` - single choke-point wiring all agents | Week 1 | [CRITICAL] |
| 13 | Final submission self-audit against all 5 challenge criteria | Week 5 | [CRITICAL] |
| 14 | Demo video script + recording direction | Week 5 | [HIGH] |
| 15 | Sahara v2.5 ASR integration (`sahara_asr.py`) - streaming, bilingual | Week 2 | [CRITICAL] |
| 16 | `classifier_agent.py` - infra-vs-legal classifier with confidence score | Week 1-2 | [CRITICAL] |
| 17 | `extraction_agent.py` - entity extraction + per-entity confidence | Week 1-2 | [CRITICAL] |
| 18 | FastAPI router (`routers/intake.py`) - thin layer over `pipeline.run_intake()` | Week 1 | [HIGH] |
| 19 | `POST /intake/{session_id}/clarify` endpoint - abstain-clarify flow | Week 2 | [HIGH] |
| 20 | Database schema (`schema.sql`) - all tables + gate_decisions | Week 1 | [CRITICAL] |
| 21 | `session.py` - DB session management | Week 1 | [HIGH] |
| 22 | `audit.py` - explainable gate decision logging | Week 2 | [HIGH] |
| 23 | `config.py` - all thresholds driven from config, zero magic numbers | Week 1 | [HIGH] |
| 24 | `requirements.txt`, `pytest.ini`, `.env.example` finalized | Week 1 | [HIGH] |
| 25 | `docker-compose.yml` - backend + Postgres, `docker-compose up` starts stack | Week 1 | [HIGH] |
| 26 | `test_gate.py` - unit tests for gate logic (mock classifier inputs) | Week 2 | [HIGH] |
| 27 | Sahara contingency: Whisper fallback if API access not confirmed by Week 1 | Week 1 | [MEDIUM] |
| 28 | Text-input fallback - same pipeline as voice, no separate codepath | Week 2 | [CRITICAL] |

### Deliverables by Week
- **Week 1:** Gate logic + pipeline wired, DB schema + Docker running, pytest passing, corpus recording starts, Sahara API status confirmed
- **Week 2:** Sahara ASR live (or Whisper fallback), text fallback done, all agents wired, SHA256 corpus frozen
- **Week 3:** Whisper + Deepgram integrated, inter-annotator agreement computed, ambiguous subset finalized
- **Week 4:** Full benchmark REPORT.md complete - WER, oracle attribution, abstention correlation, versioned results
- **Week 5:** Final self-audit, submission package, demo video direction

---

## David Akhuabe - Frontend & Artifact Generation & Docs
**14 issues** - demo layer, artifact services, and all documentation.

| # | Title | Week | Priority |
|---|-------|------|----------|
| 29 | `VoiceIntake.jsx` - recording + text-fallback input component | Week 2 | [HIGH] |
| 30 | `ClassificationView.jsx` - routing decision, confidence, reasons, clarify state | Week 2-3 | [HIGH] |
| 31 | `TicketCard.jsx` - municipal ticket artifact display | Week 2-3 | [MEDIUM] |
| 32 | `LegalBriefCard.jsx` - Legal Aid Intake Brief display | Week 2-3 | [MEDIUM] |
| 33 | `Dashboard.jsx` - main page assembling all components | Week 3 | [MEDIUM] |
| 34 | `ticket_dispatch.py` - municipal ticket generation service | Week 2 | [HIGH] |
| 35 | `legal_brief_generator.py` - Legal Aid Intake Brief generation service | Week 2 | [HIGH] |
| 36 | `docs/ARCHITECTURE.md` - system flow, module ownership, design rules | Week 1 | [HIGH] |
| 37 | `docs/SOLUTION_DESCRIPTION.md` - problem statement + key technical decisions | Week 1 | [HIGH] |
| 38 | `docs/ETHICS_INCLUSION_NOTE.md` - inclusion rationale, bias risk | Week 1 | [MEDIUM] |
| 39 | `docs/DATA_CONSENT_LOG.md` - consent tracking for every Tier A recorded speaker | Week 1 | [CRITICAL] |
| 40 | `bench/corpus/tier_b_public/` - source + cite AfriSwitch or equivalent | Week 2 | [MEDIUM] |
| 41 | Demo video production: record + edit 3-5 min submission video (OBS/Loom) | Week 5 | [HIGH] |
| 42 | Frontend scope management - thin Dashboard first if Week 4-5 get tight | Week 4-5 | [MEDIUM] |

### Deliverables by Week
- **Week 1:** Docs skeleton complete, consent log started, ticket + brief services stubbed
- **Week 2-3:** Full UI components wired to backend, artifact generation live
- **Week 4:** UI polished enough for demo video; thinned if time is tight per scope rule
- **Week 5:** Demo video recorded by Sep 13, submitted with docs

---

## Shared Responsibilities

| Task | Owner |
|------|-------|
| Git branching / PR reviews | drizzy765 (approves all PRs) |
| Benchmark REPORT.md writing | drizzy765 (author) + David (proofreads) |
| README.md - setup + run + test | drizzy765 (setup) + David (proofreads) |
| `.gitignore` hygiene | drizzy765 |
| Speaker recruitment logistics | drizzy765 (owns fully now) |

---

## Scope Rule (Non-Negotiable)
> **The benchmark is what is scored; the frontend is demo-ware.** If Weeks 4-5 get tight, David thins Dashboard/cards to the minimum the demo video needs, and drizzy765 spends reclaimed hours on corpus quality and error analysis.

---

## Blocking Dependency Chain

```
drizzy765: sahara_asr.py (#15)
    └── drizzy765: run_sahara.py (bench/models/)
            └── drizzy765: run_full_benchmark.py (#7)

drizzy765: classifier_agent.py + extraction_agent.py (#16, #17)
    └── drizzy765: gate.py::decide() (#11)
            └── drizzy765: pipeline.py::run_intake() (#12)
                    └── David: ticket_dispatch.py + legal_brief_generator.py (#34, #35)
                            └── David: VoiceIntake.jsx + ClassificationView.jsx (#29, #30)
```

---

## Load Summary

| Person | Issues | Critical | High | Medium |
|--------|--------|----------|------|--------|
| drizzy765 / Agoro | 28 | 14 | 10 | 4 |
| David Akhuabe | 14 | 1 | 7 | 6 |
| **Total** | **42** | **15** | **17** | **10** |
