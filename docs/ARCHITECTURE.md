# SautiCivic Bridge — Architecture
**This is the standing reference doc. Any agent picking up this project should read this before touching code.**

## System Flow

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

## Module Ownership Map
| Module | Responsibility |
|---|---|
| `backend/app/pipeline.py` | `run_intake(transcript, *, session_id=None, extractor=None, classifier=None, config=None) -> IntakeOutcome` — the single choke point. `session_id` links clarification chains. All new logic hangs off this function, not around it. |
| `backend/app/gate.py` | `decide()` — pure function, confidence/completeness check. Do not modify when swapping classifier/extractor backends — this is the point of the seam. |
| `backend/app/agents/classifier_agent.py` | Infra-vs-legal classification. Pluggable backend: mock (keyword-based) now, real LLM/Sahara-driven later. |
| `backend/app/agents/extraction_agent.py` | Entity extraction + per-entity confidence, feeds the gate. |
| `backend/app/services/sahara_asr.py` | Sahara v2.5 client — confirm v2.5 endpoint/auth differs from v2 used in the prior project before assuming parity. |
| `backend/app/services/ticket_dispatch.py` | Mock municipal ticket API (ServiceNow/Jira-style), generates tracking ID. |
| `backend/app/services/legal_brief_generator.py` | Structured Legal Aid Intake Brief output (PDF/doc). |
| `bench/metrics/run_oracle_comparison.py` | Runs the pipeline twice per clip (ASR transcript vs. ground truth) to attribute every failure to ASR-fault or reasoning-fault. The core rigor-demonstrating benchmark script. |
| `bench/metrics/downstream_accuracy.py` | Classification-exact / artifact-safe / artifact-corrupted — the headline metric. |
| `bench/metrics/inter_annotator_agreement.py` | Agreement score between the two independent ground-truth labelers. |
| `bench/audio_preprocessing/convert_and_validate.py` | A/B check against a reference tool before trusting any converted audio — catches preprocessing bugs before they're misattributed to model weakness. |

## Data Flow Contract (lock this before parallel work starts)
1. `POST /api/v1/intake` → accepts either audio upload or `{"text": "..."}` JSON (text fallback, always available). Returns `IntakeOutcome` with a `session_id` for clarification follow-ups.
2. Internally calls `pipeline.run_intake(transcript_or_audio)` →
   returns `IntakeOutcome`: either `{domain, artifact, entities, confidence}` or `{status: "needs_clarification", clarifying_question, reasons}`
3. Every outcome — routed or abstained — writes to the `audit_log`/`gate_decisions` table with full reasoning
4. `POST /api/v1/intake/{session_id}/clarify` → accepts `{"answer": "..."}`, re-runs the pipeline with combined context, returns a new `IntakeOutcome`

## API Versioning
All endpoints are served under `/api/v1/`. When the mock classifier is replaced by the real LLM-backed pipeline, response shapes may gain new fields (language-pair metadata, confidence sub-scores). The version prefix prevents breaking demo clients during this transition.

## Error Handling Contract
| Failure | Behavior |
|---|---|
| Sahara ASR timeout / transient error | Retry with exponential backoff (max 3 attempts, 1s → 2s → 4s). If all retries fail, return `SYSTEM_ERROR` outcome. |
| Extraction agent returns malformed / empty entities | Treat as missing entities — the gate will abstain naturally (completeness check fails). Log the malformed response for debugging. |
| Classifier returns an exception | Return `SYSTEM_ERROR` outcome with a human-readable reason. Never fall through to artifact generation. |
| Audit log DB unreachable | Buffer the audit entry to a local JSON file (`audit_buffer.jsonl`). On next successful DB write, flush the buffer. Never silently drop an audit record. |
| `SYSTEM_ERROR` is a third outcome status, distinct from `ROUTED` and `NEEDS_CLARIFICATION`. It means the pipeline could not complete — no artifact is generated, no clarifying question is asked, and the citizen sees a "please try again" message. |

## Clarification Loop
The abstain path produces a `clarifying_question`, but the architecture must also handle the citizen's *answer*:

1. `POST /api/v1/intake` returns a `session_id` with every outcome (routed or abstained).
2. `POST /api/v1/intake/{session_id}/clarify` accepts `{"answer": "..."}` — the citizen's response to the clarifying question.
3. The pipeline re-runs extraction + classification on the **combined context** (original transcript + clarification answer), then routes through the gate again.
4. The clarification chain (original → question → answer → re-classification) is stored in the audit log, linked by `session_id`.
5. Maximum 3 clarification rounds per session. After 3 abstentions, escalate to human review.

## Compute Environment — Benchmarking Runs on Colab / Cloud
> **The local dev machine does NOT run model inference.** Whisper large-v3, Sahara v2.5, and Deepgram Nova-3 corpus runs are too heavy for the local system.

| Workload | Where it runs |
|----------|--------------|
| `backend/` FastAPI server + Postgres | Local via `docker-compose up` |
| `pytest` unit tests | Local |
| `bench/metrics/downstream_accuracy.py` (text-only, no audio) | Local |
| `bench/models/run_whisper.py` — Whisper large-v3 inference | **Google Colab / cloud** |
| `bench/models/run_sahara.py` — Sahara API calls | **Google Colab / cloud** (or any machine with API key) |
| `bench/models/run_deepgram.py` — Deepgram API calls | **Google Colab / cloud** |
| `bench/audio_preprocessing/convert_and_validate.py` | **Google Colab / cloud** (ffmpeg + reference tool) |

**Workflow for cloud runs:**
1. Mount the repo in Colab (or clone it) — audio files stay in `bench/corpus/tier_a_recorded/audio/`
2. Run the relevant model script (`run_whisper.py`, `run_sahara.py`, etc.)
3. Scripts write transcript JSONs to `bench/results/transcripts/<model>/` — commit those results back
4. All metric computation (`wer.py`, `downstream_accuracy.py`, `run_full_benchmark.py`) then runs locally on the committed transcripts

**Why this matters for the scripts:** `run_whisper.py`, `run_sahara.py`, `run_deepgram.py` must write their output to a portable path (configurable `--output-dir`) so results can be pulled back from Colab without repo restructuring.

## Concurrency & Rate Limiting
- External API calls (Sahara, Deepgram, Whisper) are rate-limited per provider. The benchmark runner must respect these limits (configurable delay between clips).
- Multiple simultaneous `/intake` requests are supported — each gets its own pipeline execution context. No shared mutable state between requests.
- The audit log uses row-level locking (Postgres `INSERT`), not table-level — concurrent writes are safe.

## Configuration Management
All tunable parameters live in `backend/app/config.py` (Pydantic `BaseSettings`), loaded from environment variables with sensible defaults:
- `GATE_MIN_CLASSIFICATION_CONFIDENCE` (default: 0.70) — re-derive empirically when swapping to real classifier
- `GATE_MIN_ENTITY_CONFIDENCE` (default: 0.60)
- `DATABASE_URL` (default: `postgresql://sauticivic:sauticivic@localhost:5432/sauticivic`)
- `SAHARA_API_KEY`, `DEEPGRAM_API_KEY` — no defaults, required for real ASR
- `BENCHMARK_CLIP_DELAY_MS` (default: 200) — rate limit for benchmark runner

## Non-Negotiable Design Rules
1. **The gate must remain a pure, independently-testable function.** Do not fold gate logic into the classifier or extractor — the whole point of the seam is that the real ASR/LLM backend can be swapped in without touching abstention logic.
2. **Never treat mock-backend confidence scores as calibrated for the real classifier.** The default threshold (τ = 0.70) is tuned against the placeholder keyword-matcher. Re-derive it empirically once the real backend is wired in — do not assume it transfers.
3. **Every methodology or preprocessing fix gets a new versioned results file, never a silent overwrite.** `v1_results.json` → `v2_results.json` → ... with a documented before/after delta in `REPORT.md`.
4. **No corpus clip is added or dropped after seeing model results.** Freeze via SHA256 manifest before any model run.
5. **Frontend is demo-ware. Benchmark rigor is what's scored (30% weight).** If time runs short, this determines what gets cut.

## Known Open Items (update as resolved)
- [ ] Confirm Sahara v2.5's actual API surface (endpoints, auth, streaming protocol) — do not assume it's identical to v2
- [ ] Native speaker(s) for Tier A recording + two independent ground-truth labelers — not yet recruited as of this doc's writing
- [ ] Deepgram Nova-3 account/API key not yet set up
- [ ] Confidence threshold (τ = 0.70) is a placeholder, tied to the mock classifier — flag for re-tuning
- [ ] `SYSTEM_ERROR` outcome status not yet added to `schemas.py` — add when wiring error handling
- [ ] Clarification loop endpoint not yet implemented — scheduled for Week 2
- [ ] `config.py` created but not yet wired into `pipeline.py` and `gate.py` — wire during Week 2
