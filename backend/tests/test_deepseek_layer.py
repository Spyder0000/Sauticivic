import httpx

from app.services.deepseek_layer import (
    ArtifactDraft,
    ClarificationSuggestion,
    deterministic_question,
    parse_clarification_response,
    request_clarification,
    parse_artifact_response,
    request_artifact_draft,
)


def test_valid_deepseek_json_is_accepted():
    response = parse_clarification_response(
        '{"needs_clarification":true,"missing_field":"location","question":"Which street is affected?","reason":"Location is required."}'
    )
    assert isinstance(response, ClarificationSuggestion)
    assert response.missing_field == "location"


def test_invalid_or_empty_deepseek_json_is_rejected():
    assert parse_clarification_response("") is None
    assert parse_clarification_response('{"question":"missing fields"}') is None
    assert parse_clarification_response("not json") is None


def test_valid_and_invalid_artifact_json_are_handled_strictly():
    valid = parse_artifact_response(
        '{"title":"Blocked drain","summary":"Water is overflowing.","routing_explanation":"Required details were present."}'
    )
    assert isinstance(valid, ArtifactDraft)
    assert parse_artifact_response("") is None
    assert parse_artifact_response('{"title":"Only title"}') is None


def test_artifact_drafting_falls_back_when_provider_is_not_configured(monkeypatch):
    from app.services import deepseek_layer

    monkeypatch.setattr(deepseek_layer.settings, "deepseek_api_key", "")
    draft = request_artifact_draft(domain="infrastructure", transcript="Pothole for Allen Avenue", fields={"complaint_type": "pothole"})
    assert draft.title == "Pothole"
    assert "deterministic safety gate" in draft.routing_explanation


def test_timeout_falls_back_to_deterministic_question(monkeypatch):
    from app.services import deepseek_layer

    monkeypatch.setattr(deepseek_layer.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(deepseek_layer.settings, "deepseek_max_retries", 0)

    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(deepseek_layer.httpx, "post", timeout)
    result = request_clarification(transcript="The drain is blocked", missing_field="location")
    assert result.question == deterministic_question("location").question


def test_gate_remains_authoritative_over_optional_drafting():
    from app.pipeline import run_intake
    from app.schemas import OutcomeStatus

    outcome = run_intake("There is fire start for Allen Avenue generator")
    assert outcome.status is OutcomeStatus.EMERGENCY_RECOMMENDATION
    assert outcome.artifact is None


def test_pipeline_includes_normalized_transcript_and_case_id():
    from app.pipeline import run_intake

    outcome = run_intake("  Big pothole for Allen Avenue, e don spoil tyre.  ")
    assert outcome.normalized_transcript == "Big pothole for Allen Avenue, e don spoil tyre."
    assert outcome.artifact["case_id"].startswith("CASE-")


def test_confirmed_routed_intake_uses_optional_drafting_layer(monkeypatch):
    from app import pipeline

    monkeypatch.setattr(
        pipeline,
        "request_artifact_draft",
        lambda **_: ArtifactDraft(title="Drainage report", summary="Confirmed report.", routing_explanation="Gate-approved route."),
    )
    outcome = pipeline.run_intake("Big pothole for Allen Avenue.", allow_llm=True)
    assert outcome.artifact["draft_title"] == "Drainage report"
    assert outcome.artifact["routing_explanation"] == "Gate-approved route."
