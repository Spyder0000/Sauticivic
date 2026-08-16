#!/bin/bash
# SautiCivic Bridge — GitHub Issues Creator
# Run from repo root: bash create_issues.sh
# Requires: gh auth login

set -e

echo "Creating SautiCivic Bridge GitHub Issues..."

# ─── LABELS SETUP ─────────────────────────────────────────────────────────────
echo "Creating labels..."
gh label create "lead-drizzy765" --color "8B0000" --description "Assigned to drizzy765 / Agoro Timilehin (Group Lead)" --force
gh label create "frontend-david" --color "0969DA" --description "Assigned to David Akhuabe" --force
gh label create "priority:critical" --color "FF0000" --description "Must not slip" --force
gh label create "priority:high" --color "FF8C00" --description "Important, ship on time" --force
gh label create "priority:medium" --color "FFD700" --description "Ship if time permits" --force
gh label create "benchmarking" --color "6F42C1" --description "Benchmarking and metrics work" --force
gh label create "backend" --color "0E8A16" --description "Backend and pipeline" --force
gh label create "frontend" --color "006B75" --description "Frontend and UI" --force
gh label create "docs" --color "FBCA04" --description "Documentation" --force
gh label create "corpus" --color "E4E669" --description "Corpus and dataset" --force
gh label create "week-1" --color "BFD4F2" --description "Week 1 Aug 15-21" --force
gh label create "week-2" --color "99C2FB" --description "Week 2 Aug 22-28" --force
gh label create "week-3" --color "6AA4F8" --description "Week 3 Aug 29-Sep 4" --force
gh label create "week-4" --color "4287F5" --description "Week 4 Sep 5-11" --force
gh label create "week-5" --color "1A5DC8" --description "Week 5 Sep 12-15" --force

# ─── drizzy765 / AGORO TIMILEHIN ISSUES (28 issues — Lead owns all backend + bench) ─────────────────────────────────────────────

gh issue create \
  --title "[BENCH] Corpus setup: Tier A recording + dual-labeler ground truth" \
  --body "## Objective
Record 20-30 utterances in Nigerian Pidgin/Yoruba/English code-switch. Two independent native speakers label ground truth separately.

## Files
- bench/corpus/tier_a_recorded/audio/
- bench/corpus/tier_a_recorded/ground_truth_labeler1.json
- bench/corpus/tier_a_recorded/ground_truth_labeler2.json
- bench/corpus/tier_a_recorded/ground_truth_final.json
- bench/corpus/tier_a_recorded/ambiguous_subset.json

## Acceptance Criteria
- [ ] 20+ clips recorded and stored
- [ ] Both labeler files committed independently before reconciliation
- [ ] Disagreements moved to ambiguous_subset.json
- [ ] Reconciled final ground truth ready for model runs

## Notes
Ambiguous subset = primary test set for the abstain gate." \
  --label "lead-drizzy765,priority:critical,benchmarking,corpus,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] Implement wer.py, downstream_accuracy.py, inter_annotator_agreement.py" \
  --body "## Objective
Implement all core metric scripts in bench/metrics/.

## Files
- bench/metrics/wer.py: WER normalized + raw
- bench/metrics/downstream_accuracy.py: classification-exact / artifact-safe / artifact-corrupted
- bench/metrics/inter_annotator_agreement.py: agreement % + Cohen's kappa between labeler1 and labeler2

## Acceptance Criteria
- [ ] WER computed correctly on sample transcripts
- [ ] Artifact-corrupted metric separates silent misfiling from abstentions
- [ ] Inter-annotator agreement script outputs % agreement + kappa
- [ ] All scripts accept JSON input, output JSON results

## Notes
Artifact-corrupted must be close to 0% - this is the headline metric at 30% judging weight." \
  --label "lead-drizzy765,priority:critical,benchmarking,week-2" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] Implement run_oracle_comparison.py: ASR-fault vs reasoning-fault attribution" \
  --body "## Objective
For every Tier A clip, run pipeline.run_intake() TWICE: once on ASR transcript, once on ground-truth transcript. Classify every mismatch.

## File
bench/metrics/run_oracle_comparison.py

## Fault Categories
- ASR-fault: oracle correct, ASR run wrong - transcription caused the failure
- reasoning-fault: oracle also wrong - classifier/gate is the weak point
- concordant-correct / concordant-incorrect

## Additional
Correlate abstentions against fault type: of all gate-triggered abstentions, what fraction were warranted (ASR-fault) vs unwarranted (reasoning-fault)?

## Acceptance Criteria
- [ ] Runs on all Tier A clips without manual intervention
- [ ] Outputs per-clip attribution in JSON
- [ ] Abstention correlation computed and logged to results/
- [ ] Summary included in REPORT.md

## Notes
This is the single most rigor-demonstrating piece of the whole benchmark." \
  --label "lead-drizzy765,priority:critical,benchmarking,week-3" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] Full benchmark run: WER + downstream + oracle + abstention correlation" \
  --body "## Objective
Execute the complete benchmark suite across all 3 models (Sahara, Whisper, Deepgram) on the full corpus.

## Acceptance Criteria
- [ ] All metrics computed for all 3 models
- [ ] v1, v2, v3 results files versioned in bench/results/
- [ ] REPORT.md complete with fault attribution and version history delta
- [ ] Known issues section in REPORT.md documents mock-backend quirks transparently

## Blocking
Requires: wer.py, downstream_accuracy.py, oracle comparison, Whisper, Deepgram, Sahara from Agoro" \
  --label "lead-drizzy765,priority:critical,benchmarking,week-4" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] Audio preprocessing A/B check (convert_and_validate.py)" \
  --body "## Objective
Spot-check converted audio against the same clips run through Saharas own web UI manually. Catch preprocessing bugs before they are blamed on models.

## File
bench/audio_preprocessing/convert_and_validate.py

## Acceptance Criteria
- [ ] Compares local conversion output vs reference tool on N sample clips
- [ ] Divergences flagged as preprocessing bugs, not model weaknesses
- [ ] Results documented in REPORT.md

## Notes
This is exactly the class of bug that nearly derailed AEGIS and was the winning teams most credibility-building disclosure." \
  --label "lead-drizzy765,priority:high,benchmarking,week-3" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] Benchmark versioning: v1 to v3 results + REPORT.md with delta docs" \
  --body "## Objective
Never silently overwrite prior runs. Every methodology correction gets a new results file.

## Files
- bench/results/v1_results.json
- bench/results/v2_results.json
- bench/results/v3_results.json
- bench/results/REPORT.md (includes Known Issues section)

## Acceptance Criteria
- [ ] Each run generates a new versioned results file
- [ ] REPORT.md documents before/after delta for every version
- [ ] Known Issues section captures mock-backend quirks transparently" \
  --label "lead-drizzy765,priority:critical,benchmarking,week-4" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] run_full_benchmark.py: orchestrate all metric scripts end-to-end" \
  --body "## Objective
Single entry-point script that runs all benchmarking steps in sequence.

## File
bench/metrics/run_full_benchmark.py

## Acceptance Criteria
- [ ] Runs wer.py, downstream_accuracy.py, inter_annotator_agreement.py, run_oracle_comparison.py in order
- [ ] Outputs aggregated results to bench/results/
- [ ] CLI flags: --model, --tier, --output-version
- [ ] Idempotent: re-running does not overwrite prior results" \
  --label "lead-drizzy765,priority:critical,benchmarking,week-4" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] SHA256 corpus freeze (MANIFEST_SHA256.txt) before first model run" \
  --body "## Objective
Freeze the reconciled corpus before any model runs. No clip added or dropped after seeing results.

## File
bench/corpus/tier_a_recorded/MANIFEST_SHA256.txt

## Acceptance Criteria
- [ ] SHA256 hash of every audio file + ground truth file in manifest
- [ ] Manifest committed before first model run (verifiable via git log)
- [ ] Verification script included" \
  --label "lead-drizzy765,priority:high,benchmarking,corpus,week-2" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] Integrate Whisper large-v3 (run_whisper.py)" \
  --body "## Objective
Integrate OpenAI Whisper large-v3 as second ASR model in the benchmark.

## File
bench/models/run_whisper.py

## Acceptance Criteria
- [ ] Transcribes all Tier A + Tier B clips
- [ ] Output format identical to run_sahara.py (JSON with transcript + metadata)
- [ ] Also serves as the pipeline fallback if Sahara API access is delayed (coordinate with Agoro)" \
  --label "lead-drizzy765,priority:high,benchmarking,week-3" \
  --assignee "drizzy765"

gh issue create \
  --title "[BENCH] Integrate Deepgram Nova-3 (run_deepgram.py)" \
  --body "## Objective
Integrate Deepgram Nova-3 as the third ASR model in the benchmark.

## File
bench/models/run_deepgram.py

## Acceptance Criteria
- [ ] Transcribes all Tier A + Tier B clips
- [ ] Output format identical to run_sahara.py
- [ ] API key managed via .env / config.py" \
  --label "lead-drizzy765,priority:high,benchmarking,week-3" \
  --assignee "drizzy765"

gh issue create \
  --title "[ARCH] gate.py::decide() - confidence/completeness gate logic" \
  --body "## Objective
Implement the core confidence/completeness gate. Single choke point that fires abstain-and-ask when not confident enough.

## File
backend/app/gate.py

## Gate Rules
- Abstain if classifier confidence less than tau (default 0.70 from config.py)
- Abstain if required entity is missing or low-confidence:
  - location required for municipal ticket
  - party names required for legal brief

## Acceptance Criteria
- [ ] decide() takes ClassificationResult + entities, returns GateDecision
- [ ] All thresholds read from config.py, zero magic numbers
- [ ] Decoupled from classifier/extractor: mock can be swapped for real LLM without touching gate
- [ ] Unit testable with mock inputs

## Blocking
Blocks pipeline.py, all artifact generation, and all benchmark oracle runs" \
  --label "lead-drizzy765,priority:critical,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[ARCH] pipeline.py::run_intake() - wire all agents through gate as single choke point" \
  --body "## Objective
Implement the single choke-point that sequences extraction > classification > gate > outcome.

## File
backend/app/pipeline.py

## Flow
input > extraction_agent > classifier_agent > gate.decide() > route or abstain > artifact

## Acceptance Criteria
- [ ] run_intake() is the single entry point for all intake paths (voice + text)
- [ ] Returns IntakeOutcome (ticket | brief | abstain+question)
- [ ] Every gate decision logged via audit.py
- [ ] Config-driven thresholds, no hardcoded values" \
  --label "lead-drizzy765,priority:critical,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[SUBMIT] Final submission self-audit against all 5 challenge criteria" \
  --body "## Objective
Run through the full submission checklist against all 5 judging criteria before submitting.

## Checklist
- [ ] Real native-speaker-validated recorded corpus
- [ ] TWO independent labelers, agreement reported, disagreements as ambiguous subset
- [ ] Frozen corpus hash before any model was run
- [ ] Confidence/completeness gate as a real architectural node
- [ ] Oracle-vs-ASR run attributing every failure to correct layer
- [ ] Abstention rate correlated against fault type
- [ ] Audio preprocessing A/B-checked
- [ ] Every methodology correction versioned and disclosed
- [ ] Text-input fallback built from day one
- [ ] Consent log for every recorded speaker
- [ ] requirements.txt committed
- [ ] Demo video recorded and reviewed" \
  --label "lead-drizzy765,priority:critical,week-5" \
  --assignee "drizzy765"

gh issue create \
  --title "[SUBMIT] Demo video script + recording direction" \
  --body "## Objective
Finalize the 3-5 min demo video script and oversee recording. Must be done by Sep 13.

## Script Outline
1. 30s: Problem statement - who this serves and why existing tools fail them
2. 60s: Live demo: clear infrastructure complaint > ticket generated
3. 60s: Live demo: ambiguous complaint > gate abstains > clarifying question > correct routing
4. 30s: Text fallback input showing same pipeline without audio
5. 30s: Benchmark results highlight - artifact-corrupted rate, oracle comparison, abstention correlation
6. 30s: Architecture diagram walkthrough - gate as safety mechanism

## Acceptance Criteria
- [ ] Script written and reviewed by full team
- [ ] Video recorded using OBS Studio or Loom
- [ ] Recorded by Sep 13 (2-day editing buffer before Sep 15 deadline)" \
  --label "lead-drizzy765,priority:high,week-5" \
  --assignee "drizzy765"

# (continued above - Agoro Timilehin is drizzy765) ────────────────────────────────────────

gh issue create \
  --title "[BACKEND] Sahara v2.5 ASR integration (sahara_asr.py) - streaming, bilingual" \
  --body "## Objective
Integrate Sahara v2.5 as the primary ASR service. Streaming-capable and bilingual/code-switch-aware.

## File
backend/app/services/sahara_asr.py

## Acceptance Criteria
- [ ] Accepts audio bytes or file path, returns transcript + language-pair detected
- [ ] Streaming mode supported
- [ ] Falls back gracefully if API unavailable without crashing
- [ ] API key loaded from config.py / .env
- [ ] Confirm API access by end of Week 1 - activate contingency if blocked

## Blocking
Blocks bench/models/run_sahara.py (drizzy765)" \
  --label "lead-drizzy765,priority:critical,backend,week-2" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] classifier_agent.py - infra-vs-legal classifier with confidence score" \
  --body "## Objective
Implement the classifier agent with pluggable backend (mock now, real LLM later).

## File
backend/app/agents/classifier_agent.py

## Output
ClassificationResult(domain: Domain, confidence: float, reasons: list[str])

## Acceptance Criteria
- [ ] Pluggable backend: mock implements same interface as real LLM
- [ ] Outputs domain (infra or legal) + confidence 0.0-1.0 + human-readable reason strings
- [ ] Reasons used by gate for explainability and by ClassificationView.jsx for display
- [ ] Unit testable with mock inputs" \
  --label "lead-drizzy765,priority:critical,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] extraction_agent.py - entity extraction + per-entity confidence" \
  --body "## Objective
Implement entity extraction agent. Per-entity confidence is critical for the gate to decide whether to abstain.

## File
backend/app/agents/extraction_agent.py

## Entities to Extract
- location (required for ticket)
- party_names (required for legal brief)
- complaint_type
- urgency_cues

## Output
list[Entity(name: str, value: str, confidence: float)]

## Acceptance Criteria
- [ ] Per-entity confidence score 0.0-1.0 on each extracted entity
- [ ] Missing entities represented as Entity with confidence=0.0 (not omitted)
- [ ] Pluggable backend same as classifier_agent" \
  --label "lead-drizzy765,priority:critical,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] FastAPI router (routers/intake.py) - thin layer over pipeline.run_intake()" \
  --body "## Objective
Implement the FastAPI intake router. Keep it thin - no business logic here.

## File
backend/app/routers/intake.py

## Endpoints
- POST /intake: accepts text or audio, calls pipeline.run_intake(), returns IntakeOutcome
- POST /intake/{session_id}/clarify: handles user response to abstain question

## Acceptance Criteria
- [ ] Both endpoints wired to pipeline.run_intake() with no business logic in router
- [ ] Correct HTTP status codes (200 ok, 422 validation error)
- [ ] OpenAPI docs auto-generated and accurate
- [ ] Text and audio both accepted (content-type aware)" \
  --label "lead-drizzy765,priority:high,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] POST /intake/{session_id}/clarify endpoint - abstain to clarify flow" \
  --body "## Objective
When gate abstains it returns a clarifying question. This endpoint handles the users answer and re-runs pipeline.

## File
backend/app/routers/intake.py (extend existing router)

## Acceptance Criteria
- [ ] Accepts session_id + user clarification text
- [ ] Re-runs pipeline.run_intake() with enriched context
- [ ] Session state persisted in DB between calls
- [ ] Gate decision logged for the re-run as a separate audit entry" \
  --label "lead-drizzy765,priority:high,backend,week-2" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] Database schema (schema.sql) - complaints, classifications, artifacts, audit_log, gate_decisions" \
  --body "## Objective
Implement the Postgres schema for all persistent state.

## File
backend/app/db/schema.sql

## Tables Required
- complaints: raw intake (text/audio ref, session_id, timestamp)
- classifications: domain, confidence, reasons
- artifacts: type (ticket | brief | abstain), content JSON, session_id
- audit_log: every action with timestamp and actor
- gate_decisions: gate outcome, reasons, thresholds used, confidence scores

## Acceptance Criteria
- [ ] All tables with proper FK constraints
- [ ] gate_decisions table captures full explainability data
- [ ] Schema runnable via docker-compose up init scripts" \
  --label "lead-drizzy765,priority:critical,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] session.py - database session management" \
  --body "## Objective
Implement SQLAlchemy or asyncpg session management for the database.

## File
backend/app/db/session.py

## Acceptance Criteria
- [ ] Connection pooling configured
- [ ] Async session support (FastAPI compatible)
- [ ] Session cleanup on request completion
- [ ] DB URL loaded from config.py / .env" \
  --label "lead-drizzy765,priority:high,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] audit.py - explainable gate decision logging" \
  --body "## Objective
Every gate decision must be logged with full reasons - not just the outcome but WHY.

## File
backend/app/audit.py

## What to Log
- Gate decision (route or abstain)
- Classifier confidence + threshold at time of decision
- Per-entity confidence scores
- Which entity/threshold triggered abstention if applicable
- ASR transcript used
- Timestamp + session_id

## Acceptance Criteria
- [ ] log_gate_decision() called from pipeline.run_intake() on every run
- [ ] Data retrievable for benchmark oracle comparison (drizzy765 issue)
- [ ] No excess PII logged beyond what is needed for audit" \
  --label "lead-drizzy765,priority:high,backend,week-2" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] config.py - all thresholds config-driven, no magic numbers in source" \
  --body "## Objective
Every threshold in the system must come from config.py. No hardcoded values in gate.py or elsewhere.

## File
backend/app/config.py

## Values to Configure
- gate_confidence_threshold (default 0.70)
- gate_entity_confidence_threshold
- required_entities_for_ticket (list)
- required_entities_for_brief (list)
- sahara_api_url, sahara_api_key
- database_url

## Acceptance Criteria
- [ ] Pydantic Settings or equivalent with env var override
- [ ] All values documented in .env.example
- [ ] Zero magic numbers in gate.py, pipeline.py, or agents" \
  --label "lead-drizzy765,priority:high,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] requirements.txt, pytest.ini, .env.example finalized" \
  --body "## Objective
Ensure the project is fully reproducible from a clean clone.

## Files
- backend/requirements.txt
- backend/pytest.ini
- .env.example

## Acceptance Criteria
- [ ] requirements.txt has pinned versions for all dependencies
- [ ] pytest.ini configures test discovery correctly
- [ ] .env.example documents every env var with example values (no real secrets)
- [ ] pip install -r requirements.txt and pytest passes on a clean environment" \
  --label "lead-drizzy765,priority:high,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[INFRA] docker-compose.yml - backend + Postgres, docker-compose up starts full stack" \
  --body "## Objective
docker-compose up starts both FastAPI backend and Postgres DB, runs schema.sql on first boot.

## File
infra/docker-compose.yml

## Services
- db: Postgres 16, initialized with schema.sql
- backend: FastAPI app, depends on db

## Acceptance Criteria
- [ ] docker-compose up -d starts both services
- [ ] Schema applied automatically on first start
- [ ] Health check on backend container
- [ ] README quick-start instructions match this setup" \
  --label "lead-drizzy765,priority:high,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[TEST] test_gate.py - unit tests for gate logic with mock classifier inputs" \
  --body "## Objective
Comprehensive unit tests for gate.py::decide() using mock classifier and extractor outputs.

## File
backend/tests/test_gate.py

## Test Cases Required
- [ ] High confidence + all entities present: routes correctly
- [ ] Confidence below threshold: abstains
- [ ] Missing required location entity for ticket: abstains
- [ ] Missing party names for legal brief: abstains
- [ ] Borderline confidence exactly at threshold: routes (not abstains)
- [ ] Ambiguous domain equal confidence on both: abstains
- [ ] All gate decisions produce loggable reason strings

## Acceptance Criteria
- [ ] pytest passes with 100% of the above cases
- [ ] Tests are independent (no shared state)" \
  --label "lead-drizzy765,priority:high,backend,week-2" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] Sahara contingency: Whisper fallback if API access not confirmed by Week 1" \
  --body "## Objective
If Sahara v2.5 API access is not confirmed by end of Week 1, activate Whisper large-v3 fallback plan.

## Contingency Steps
1. Use Whisper large-v3 as primary ASR for pipeline development
2. Document substitution transparently in bench/results/REPORT.md
3. sahara_asr.py remains the target interface - Whisper implements the same interface
4. Plug Sahara back in when access confirmed without reworking pipeline

## Acceptance Criteria
- [ ] Confirm Sahara API access status by Aug 21
- [ ] If blocked: Whisper integrated and pipeline running by Aug 21
- [ ] Substitution documented in REPORT.md by Week 2" \
  --label "lead-drizzy765,priority:medium,backend,week-1" \
  --assignee "drizzy765"

gh issue create \
  --title "[BACKEND] Text-input fallback - same pipeline as voice, no separate codepath" \
  --body "## Objective
Text input must share the identical pipeline as voice input. No separate handler - direct lesson from Phase 1.

## Acceptance Criteria
- [ ] POST /intake accepts both text body and audio file in same endpoint
- [ ] Text input bypasses ASR step only, runs identical extraction > classifier > gate > artifact
- [ ] Text fallback demonstrated in demo video
- [ ] VoiceIntake.jsx has text input visible alongside recording button (David's issue)" \
  --label "lead-drizzy765,priority:critical,backend,week-2" \
  --assignee "drizzy765"

# ─── DAVID AKHUABE ISSUES (14 issues) ─────────────────────────────────────────

gh issue create \
  --title "[FRONTEND] VoiceIntake.jsx - recording + text-fallback input component" \
  --body "## Objective
Main intake component: voice recording AND text input visible together from day one.

## File
frontend/src/components/VoiceIntake.jsx

## Acceptance Criteria
- [ ] Voice recording button with visual feedback (recording indicator)
- [ ] Text fallback input always visible alongside recording button
- [ ] Both inputs call the same POST /intake endpoint
- [ ] Loading/processing state shown while waiting for pipeline response
- [ ] Error handling: user-friendly message on API failure" \
  --label "frontend-david,priority:high,frontend,week-2" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[FRONTEND] ClassificationView.jsx - routing decision, confidence, reasons, clarify state" \
  --body "## Objective
Display the full gate output: routing decision, confidence score, reasons, and Needs Clarification state.

## File
frontend/src/components/ClassificationView.jsx

## States to Display
1. Routed: domain (infra or legal), confidence score, reasons list
2. Clarification needed: clarifying question, input for user response, re-submit button
3. Loading: skeleton/spinner while pipeline processes

## Acceptance Criteria
- [ ] Confidence score displayed visually (progress bar or badge)
- [ ] Reasons list shown in collapsible section
- [ ] Clarify state: question prominent, response input + re-submit button
- [ ] Sends POST /intake/{session_id}/clarify on re-submit" \
  --label "frontend-david,priority:high,frontend,week-2" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[FRONTEND] TicketCard.jsx - municipal ticket artifact display" \
  --body "## Objective
Display a generated municipal infrastructure ticket artifact.

## File
frontend/src/components/TicketCard.jsx

## Data to Display
- Complaint type, location, urgency level, ticket ID, status

## Acceptance Criteria
- [ ] Clear visual hierarchy (ticket ID, type, location prominent)
- [ ] Copy-to-clipboard for ticket reference
- [ ] Responsive layout" \
  --label "frontend-david,priority:medium,frontend,week-2" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[FRONTEND] LegalBriefCard.jsx - Legal Aid Intake Brief display" \
  --body "## Objective
Display a generated Legal Aid Intake Brief artifact.

## File
frontend/src/components/LegalBriefCard.jsx

## Data to Display
- Grievance type, party names, complaint summary, recommended next steps, brief reference ID

## Acceptance Criteria
- [ ] Sensitive content handled carefully
- [ ] Print-friendly layout
- [ ] Responsive layout" \
  --label "frontend-david,priority:medium,frontend,week-2" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[FRONTEND] Dashboard.jsx - main page assembling all components" \
  --body "## Objective
Main page assembling VoiceIntake, ClassificationView, and artifact cards.

## File
frontend/src/pages/Dashboard.jsx

## Acceptance Criteria
- [ ] VoiceIntake at top
- [ ] ClassificationView shows after submission
- [ ] Correct artifact card (Ticket or Brief) shown based on routing outcome
- [ ] Clarification flow visible and functional

## SCOPE RULE (Section 7)
This component gets thinned FIRST if Week 4-5 get tight. Document any cuts in a comment." \
  --label "frontend-david,priority:medium,frontend,week-3" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[SERVICE] ticket_dispatch.py - municipal ticket generation service" \
  --body "## Objective
Generate a structured municipal infrastructure ticket from the pipeline output.

## File
backend/app/services/ticket_dispatch.py

## Input
IntakeOutcome with domain=INFRA and entities (location, complaint_type, urgency)

## Output
Ticket JSON: ticket_id, complaint_type, location, urgency, generated_at, status

## Acceptance Criteria
- [ ] Generates unique ticket_id
- [ ] Persists ticket to artifacts table in DB
- [ ] Returns structured ticket JSON matching schema.py dataclass
- [ ] Raises clear error if required location entity is missing" \
  --label "frontend-david,priority:high,backend,week-2" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[SERVICE] legal_brief_generator.py - Legal Aid Intake Brief generation service" \
  --body "## Objective
Generate a structured Legal Aid Intake Brief from the pipeline output.

## File
backend/app/services/legal_brief_generator.py

## Input
IntakeOutcome with domain=LEGAL and entities (party_names, grievance_type, urgency)

## Output
Brief JSON: brief_id, grievance_type, complainant, respondent, summary, next_steps, generated_at

## Acceptance Criteria
- [ ] Generates unique brief_id
- [ ] Persists brief to artifacts table in DB
- [ ] Returns structured brief JSON matching schema.py dataclass
- [ ] Raises clear error if required party_names entity is missing" \
  --label "frontend-david,priority:high,backend,week-2" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[DOCS] docs/ARCHITECTURE.md - system flow, module ownership, design rules" \
  --body "## Objective
Comprehensive architecture document including the corrected gate node and all design decisions.

## File
docs/ARCHITECTURE.md

## Content Required
- System flow diagram (ASCII or Mermaid)
- Module ownership table (who owns what file)
- Key design decisions and tradeoffs
- Sequence diagram for voice intake > ticket flow
- Sequence diagram for ambiguous input > abstain > clarify > brief flow

## Acceptance Criteria
- [ ] Architecture accurately reflects the implemented system (update as system evolves)
- [ ] All three team members can navigate the codebase using this doc" \
  --label "frontend-david,priority:high,docs,week-1" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[DOCS] docs/SOLUTION_DESCRIPTION.md - problem statement + key technical decisions" \
  --body "## Objective
Submission-quality solution description for challenge judges.

## File
docs/SOLUTION_DESCRIPTION.md

## Content Required
- Who this serves and why existing tools fail them
- Key technical decisions (gate, oracle comparison, abstention as first-class outcome)
- Why artifact-corrupted approaching 0% is the right headline metric
- What makes this different from Phase 1 Sauti Ledger

## Acceptance Criteria
- [ ] Clear non-technical problem statement readable by judges without ML background
- [ ] Technical decisions explained with tradeoffs
- [ ] Updated in Week 5 to reflect actual built system" \
  --label "frontend-david,priority:high,docs,week-1" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[DOCS] docs/ETHICS_INCLUSION_NOTE.md - inclusion rationale and bias risk" \
  --body "## Objective
Document ethics and inclusion considerations for this project.

## File
docs/ETHICS_INCLUSION_NOTE.md

## Content Required
- Who is served and why this population is underserved by existing civic tools
- Language inclusion rationale: Nigerian Pidgin, Yoruba, English code-switching
- Bias risks: model performance disparities across language pairs, urban vs rural accents
- Mitigation: dual-labeler ground truth, ambiguous subset as gate test set
- Data minimization: what PII is collected and why

## Acceptance Criteria
- [ ] Completed by end of Week 1 - cannot be retrofitted" \
  --label "frontend-david,priority:medium,docs,week-1" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[DOCS] docs/DATA_CONSENT_LOG.md - consent tracking for every Tier A recorded speaker" \
  --body "## Objective
Track informed consent for every real speaker recorded in Tier A corpus. Required from Week 1.

## File
docs/DATA_CONSENT_LOG.md

## Required Per Speaker Entry
- Speaker pseudonym (no real names in the log)
- Date of consent
- Consent scope (this project only vs broader research)
- Recording session ID
- Whether consent covers re-recording or corrections

## Acceptance Criteria
- [ ] Entry created for every speaker BEFORE their recording is committed
- [ ] Log format consistent for auditing
- [ ] No real names - pseudonyms only" \
  --label "frontend-david,priority:critical,docs,corpus,week-1" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[CORPUS] bench/corpus/tier_b_public/ - source and cite AfriSwitch or equivalent dataset" \
  --body "## Objective
Source and document the public code-switching dataset for Tier B benchmarking.

## Directory
bench/corpus/tier_b_public/

## Requirements
- Use AfriSwitch or similar public code-switching dataset
- Cite properly, do not redistribute
- Cover language pairs Tier A does not have

## Acceptance Criteria
- [ ] Dataset sourced and documented in a README within tier_b_public/
- [ ] Full citation included (author, year, license)
- [ ] Only the subset we use is referenced (no full redistribution)
- [ ] Language pair coverage documented" \
  --label "frontend-david,priority:medium,corpus,week-2" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[SUBMIT] Demo video production: record + edit 3-5 min submission video" \
  --body "## Objective
Produce the final 3-5 minute submission demo video using OBS Studio or Loom. Must be done by Sep 13.

## Script Outline (from drizzy765 script issue)
1. 30s: Problem statement
2. 60s: Clear complaint > ticket generated
3. 60s: Ambiguous > gate abstains > clarify > correct routing
4. 30s: Text fallback demo
5. 30s: Benchmark results highlight
6. 30s: Architecture diagram walkthrough

## Acceptance Criteria
- [ ] Video recorded by Sep 13 (2-day editing buffer)
- [ ] Reviewed by drizzy765 before submission
- [ ] Uploaded to submission platform by Sep 15

## Notes
Coordinate with drizzy765 on script finalization before recording." \
  --label "frontend-david,priority:high,week-5" \
  --assignee "davidakhuabe"

gh issue create \
  --title "[SCOPE] Frontend scope management: thin Dashboard if Week 4-5 get tight (Section 7 rule)" \
  --body "## Objective
Standing scope rule: benchmark is what is scored, frontend is demo-ware.

## Rule
If Weeks 4-5 get tight:
1. Thin Dashboard.jsx and card components to minimum needed for demo video
2. Reclaimed hours go to corpus quality, labeler agreement, error analysis (drizzy765)
3. Document all cuts with a comment in the thinned files

## This is a standing team agreement - not a decision to make in the moment.

## Acceptance Criteria
- [ ] Scope rule acknowledged by all team members (comment on this issue to confirm)
- [ ] If cuts are made: documented in the thinned files and noted in REPORT.md" \
  --label "frontend-david,priority:medium,frontend,week-4" \
  --assignee "davidakhuabe"

echo ""
echo "All 42 GitHub issues created successfully!"
echo ""
echo "Issues by assignee:"
echo "  drizzy765 / Agoro Timilehin (Lead): 28 issues - Benchmarking + Full Backend Pipeline"
echo "  David Akhuabe:        14 issues - Frontend, Artifact Services, Docs"
echo ""
echo "Username note: Update agorotimilehin and davidakhuabe in this script to their actual GitHub usernames if different."
