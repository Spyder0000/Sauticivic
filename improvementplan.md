# SautiCivic Improvement Plan

You’re already around **9.1/10 technically**. To push the complete submission toward **9.7–10/10**, don’t add more complexity. Close the few evidence, product, and storytelling gaps judges could attack.

## 1. Increase speaker diversity — highest priority

Your weakest point is **30 recordings from only two speakers**.

Record a small standardized `don/don’t` stress test with **5–8 additional people**:

* Different Nigerian accents and regions.
* Both male and female speakers.
* Around 5–10 short sentences per person.
* Include different phones, speaking speeds, and mild background noise.
* Run exactly the same audio through all four ASRs.

You don’t need to rebuild the full dataset. Even 40–60 additional targeted clips would make your central discovery much more defensible.

Report:

* inversion rate per model;
* inversion rate per speaker/accent;
* clean versus noisy conditions;
* confidence intervals, if possible.

This could raise dataset strength from **7.5/10 to roughly 9/10**.

## 2. Make the product feel deployable

The demo must look like a genuine civic-intake workflow, not an ML dashboard.

The ideal flow is:

1. Citizen records a complaint naturally.
2. Live transcript appears.
3. System extracts location, incident, urgency, and relevant people.
4. Citizen reviews and confirms the interpretation.
5. Safety gate evaluates the complaint.
6. System either:

   * generates a structured civic ticket;
   * generates a legal-aid brief;
   * asks a specific clarification question; or
   * escalates an emergency.

7. Citizen receives a tracking/reference number.

Show the final artifact with:

* original audio;
* original and normalized transcript;
* extracted entities;
* department and urgency;
* explanation for the routing decision;
* consent status;
* timestamp and case ID;
* correction and deletion controls.

## 3. Demonstrate three carefully chosen cases

Your live demo should use only three stories:

### Case 1: Normal civic complaint

A pothole or streetlight complaint is transcribed and converted into a municipal ticket.

### Case 2: Polarity inversion

Use the domestic-abuse example:

> “My husband don chase me and the children comot for house…”

Compare Sahara with a model that outputs *“My husband don’t chase me…”*. Then show how SautiCivic prevents the corrupted interpretation from becoming a legal record.

### Case 3: Adversarial safety case

Show an apparently ordinary infrastructure complaint containing active violence, fire, extortion, or illegal demolition. The system must block ordinary dispatch and escalate safely.

These three cases demonstrate **utility, linguistic innovation, and safety** without overwhelming the judges.

## 4. Add human evaluation

Technical metrics alone cannot fully prove that the generated tickets and legal briefs preserve meaning.

Ask **two or three independent reviewers**—ideally native Pidgin speakers, legal/public-service professionals, or both—to score anonymized outputs on:

* meaning preservation;
* correct urgency;
* correct department;
* completeness;
* harmful omission;
* artifact usability.

Calculate agreement using Cohen’s kappa for two annotators or Krippendorff’s alpha for more flexible annotation.

Even a small blinded review would address the current **single-labeler limitation**.

## 5. Strengthen your safety evaluation

Your 10/10 adversarial result is excellent, but ten examples are still limited. Expand to approximately **20–30 high-quality cases** covering:

* active fire disguised as a utility complaint;
* domestic abuse disguised as a tenancy dispute;
* extortion disguised as a payment complaint;
* illegal demolition disguised as waste removal;
* armed violence near damaged infrastructure;
* child safeguarding;
* medical emergency;
* prompt injection inside a spoken complaint;
* attempts to force the system to expose another citizen’s data;
* ambiguous cases where clarification is the correct response.

Separate them into:

* true emergencies;
* legal/criminal cases;
* ordinary civic issues;
* ambiguous cases;
* malicious or manipulative inputs.

This proves that the gate is not merely matching a few memorized phrases.

## 6. Fix confidence calibration

The **30.9% Expected Calibration Error** is the ugliest number in the report.

Before submission:

* replace mock confidence with real classifier probabilities if possible;
* use a validation set to tune thresholds;
* create a reliability diagram;
* report selective accuracy at different coverage levels;
* show that accuracy improves as the system abstains more.

A useful table would be:

| Confidence threshold | Coverage | Correct routing | Corrupted artifacts |
| -------------------- | -------: | --------------: | ------------------: |
| 0.60                 |        … |               … |                   … |
| 0.70                 |        … |               … |                   … |
| 0.80                 |        … |               … |                   … |
| 0.90                 |        … |               … |                   … |

The product story should be: **SautiCivic knows when not to act.**

## 7. Measure deployment performance

Add the practical metrics currently missing or underemphasized:

* median and p95 transcription latency;
* complete audio-to-ticket latency;
* API failure rate;
* estimated cost per complaint;
* performance under weak connectivity;
* retry and timeout behavior;
* audio upload size;
* response when one provider is unavailable.

Judges assessing technical execution will want evidence that the pipeline works beyond a controlled notebook.

## 8. Show responsible AI inside the product

Don’t leave privacy and consent only in documentation. Put them visibly in the workflow:

* clear recording consent;
* ability to review and correct the transcript;
* explicit confirmation before submission;
* data-retention explanation;
* delete-my-recording option;
* PII redaction;
* human escalation for serious cases;
* no automatic law-enforcement dispatch;
* encryption and access-control explanation;
* audit trail showing what the model changed.

For legal and domestic-abuse complaints, avoid exposing sensitive information through unsafe notifications or shared devices.

## 9. Obtain real user or institutional validation

A small piece of external evidence would considerably improve your impact score:

* test with 5–10 potential users;
* speak to a legal-aid clinic, local-government worker, NGO, or civic organization;
* obtain a short written expression of pilot interest if possible;
* document the current manual process and how SautiCivic improves it.

Report concrete findings such as:

* completion rate;
* time taken;
* corrections required;
* perceived trust;
* whether the generated artifact was usable.

A genuine pilot pathway is more valuable than adding another model.

## 10. Simplify the report’s opening

Put this on the first page:

> **WER says Sahara and Gemini are close:** 12.4% vs 14.8%  
> **Meaning preservation says otherwise:** 0 vs 5 polarity inversions  
> **Real consequence:** “He has chased me out” becomes “He hasn’t chased me out”  
> **SautiCivic’s response:** detect uncertainty, stop unsafe action, clarify or escalate

Then move dense methodology behind that opening.

## Best order of execution

If the deadline is extremely close, prioritize:

1. Stabilize the complete product workflow.
2. Add 5–8 speakers to the polarity stress test.
3. Create the three-case demo.
4. Improve the opening page and pitch.
5. Conduct a small blinded human review.
6. Expand adversarial testing.
7. Add latency, cost, reliability, and calibration results.
8. Secure user or partner validation.

The path to 10 is not “more AI.” It is **broader evidence, an undeniable live product, and a pitch judges can repeat from memory**. Your winning identity should remain:

> **The system that discovered standard ASR metrics can hide the reversal of African citizens’ complaints—and prevents those errors from becoming real-world actions.**
