# Ethics & Inclusion Note: SautiCivic Bridge

**Sahara CodeSwitch Africa Challenge 2026 — Legal & Public Services Track**

## 1. Sociolinguistic Inclusion & Creole Grammar Fidelity
Automated public service intake tools in West Africa have historically imposed a linguistic penalty on citizens who communicate in indigenous languages or English-lexified Creoles like Nigerian Pidgin (Naija). Standard automated systems either fail outright or normalize colloquial speech into standard English, stripping aspectual markers and misinterpreting user intent.

SautiCivic Bridge treats code-switching and Nigerian Pidgin as primary, legitimate communicative registers. The core metric of our benchmark—**aspectual polarity inversion**—was specifically formulated to protect citizens from systemic erasure: converting the completive aspect marker *don* into the negative contraction *don't* silently reverses citizen grievances into denials, which could render complaints non-actionable in critical civic workflows. Nigerian Pidgin is used by millions of speakers and serves as a widely used lingua franca; evaluating models specifically for grammatical preservation of *don* supports linguistic equity.

## 2. Informed Consent & Speaker Privacy
- **Consent Protocols:** All primary audio contributors for Tier A (`SPK-01`, `SPK-02`) and the Tier A Multi-Speaker Validation suite (`SPK-03`, `SPK-04`, `SPK-05`) provided explicit, informed consent for academic benchmarking and research distribution. Detailed records are maintained in `docs/DATA_CONSENT_LOG.md` and `bench/corpus/tier_a_multispeaker_validation/speaker_metadata.json`.
- **Rigorous PII Minimization:** All recordings were performed using consented recordings of realistic Nigerian Pidgin/English grievance scenarios with simulated names and locations. No real citizen telephone numbers, national identity numbers, or private residential addresses are contained in the transcripts.
- **Controlled Access & Anonymity:** The evaluation uses pseudonymous speaker IDs, documented consent, restricted benchmark access, and PII-minimized metadata. Because voice recordings may themselves be identifying, raw audio requires controlled access and retention. Dialectal and regional accent attributions are treated cautiously: Tier A-MSV metadata explicitly records regional accent as unverified to avoid ungrounded demographic assertions.

## 3. Safety-Critical Harm Avoidance & Responsible Abstention
In high-stakes public service intake, false confidence is dangerous. Automated triage must never guess when a mistake could cause physical harm or legal prejudice:
- **Two-Tier Safety Gate:** Our deterministic risk gate (`backend/app/gate.py`) intercepts life-safety emergencies (Tier 1: active fires, structural collapses) and criminal/extortion abuses (Tier 2: unlawful evictions, taskforce extortion, violence).
- **Abstention as Safe Failure:** When transcription ambiguity, entity incompleteness, or low classification confidence occurs, the system safely abstains with structured clarification questions rather than dispatching a flawed artifact. Across the benchmark, SautiCivic achieved 0.0% artifact corruption and 100.0% adversarial harm avoidance.

## 4. Algorithmic Transparency & Auditability
Every pipeline execution produces a persistent, transparent audit record containing:
1. Exact raw and normalized ASR transcripts.
2. Extracted entities and confidence estimates.
3. Decision rationale for routing or gate abstention.
4. Deterministic SHA-256 audio and artifact hashes.

Decisions are never black-box: citizens and caseworkers have full visibility into why a grievance was routed or why clarifying information was requested.
