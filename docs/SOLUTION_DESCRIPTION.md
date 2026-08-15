# SautiCivic Bridge — Solution Description
**Sahara CodeSwitch Africa Challenge — Legal & Public Services Track**

## The Problem
Two distinct groups of African citizens are structurally disenfranchised by the same barrier: English-only, text-based reporting systems. The vast majority of infrastructure faults go unreported through official channels — citizens default to word-of-mouth or social media, where complaints are neither tracked nor actionable. At legal aid clinics, paralegals routinely spend the bulk of each intake session manually translating spoken, code-switched testimony into the structured briefs that the formal system requires.

1. **Municipal infrastructure complaints** (burst pipes, downed power lines, road damage) go unreported or misrouted when citizens can't navigate a typed-English portal.
2. **Legal aid seekers** (wrongful eviction, wage theft, police harassment) explain their situation in colloquial, code-switched speech to overwhelmed paralegals who spend hours manually translating spoken testimony into formal intake briefs.

Both problems share a root cause: the system only listens in one language, in one register, in text. Neither group is well-served by voice tools that treat code-switching as noise to normalize away rather than signal to understand.

## Target Users
Citizens across Nigeria (and extensible to other African contexts) reporting either an infrastructure hazard or a legal grievance, speaking naturally in Nigerian Pidgin/Yoruba/English code-switched speech — not adapted English, not typed forms.

## Differentiation
Existing civic tech tools (e.g., FixMyStreet, SeeClickFix) assume English-literate, text-comfortable users — they don't handle voice input at all, let alone code-switched speech. Voice-based legal aid tools (where they exist) treat code-switching as noise to be normalized, losing the contextual cues embedded in language choice. SautiCivic is different because it treats code-switching as signal: a speaker who switches from English to Pidgin mid-sentence when describing an emotional event is providing information, not creating a transcription problem.

## The Solution
A single voice intake pipeline that:
1. Transcribes a citizen's spoken complaint via Sahara v2.5, preserving code-switched content rather than normalizing it away
2. Extracts key entities (location, party names, complaint type, urgency signals)
3. Classifies the complaint as infrastructure or legal
4. **Either generates the correct structured downstream artifact (a dispatched municipal ticket, or a Legal Aid Intake Brief) — or abstains and asks a clarifying question if confidence or entity completeness is insufficient to act safely**
5. Logs every decision, including every abstention, to an explainable audit trail

The abstain mechanism exists because the cost of a wrong guess here is not neutral: silently misfiling a domestic-violence grievance as a pothole ticket is the exact failure this system is built to prevent, not just a WER statistic to minimize.

## Key Technical Decisions
- **One shared pipeline, two output templates, not two separate products.** Both problems require identical ASR → extraction → classification stages; only the downstream artifact differs. This avoids duplicating the hardest engineering work while still demonstrating breadth.
- **Abstention is a first-class architectural outcome, not an afterthought.** A confidence/completeness gate sits between classification and artifact generation — this is what turns "the system can ask a clarifying question instead of guessing" from an aspiration into something the architecture can actually produce and the benchmark can actually measure.
- **Downstream-task accuracy, not WER alone, is the headline benchmark metric.** Following a prior-project lesson that a low WER can still produce a corrupted or unusable downstream result — we measure whether transcription errors actually change the classification or corrupt an extracted entity, and separately, whether that failure originates in the ASR layer or the reasoning layer (via an oracle-vs-ASR comparison run).
- **Real, native-speaker-validated recorded corpus, not just a borrowed public dataset.** Two independent labelers score ground truth separately; disagreement cases are kept as a documented "ambiguous" test set rather than silently resolved by one person's judgment.
- **Text-input fallback built alongside voice input from day one**, not patched in under deadline pressure — a direct lesson from a prior build where browser audio encoding (webm/opus) proved incompatible with a streaming ASR API's expected format (PCM), discovered only hours before a deadline.

## Scalability
The pipeline's architecture is language-pair agnostic by design. Sahara v2.5 handles the ASR layer; the extraction and classification agents operate on transcribed text. Adding a new language pair (e.g., Swahili/English for East African contexts) requires only: (1) an ASR model that supports the pair, and (2) updated keyword vocabularies or fine-tuned prompts for the extraction/classification agents. The gate, pipeline orchestration, and artifact generators require zero changes.

## Demo Scope
The submission demo shows the end-to-end pipeline on representative code-switched complaints — voice input, transcription, classification, gate decision, and artifact generation. The UI is a functional proof-of-concept, not a production interface. Per the project's standing scope rule (Section 7 of the implementation plan), benchmark rigor and pipeline correctness take priority over frontend polish.

## Category
Legal & Public Services — civic reporting, complaints, justice access.

## Ethics
All real recorded speakers provide documented consent (`docs/DATA_CONSENT_LOG.md`). No production personal data used at any stage. Every classification and abstention decision is logged with a human-readable reason, auditable by both the citizen and any human reviewer.
