"""Regression tests for clarification-round exhaustion."""

from app.routers.intake import ClarifyRequest, intake_clarify
from app.session_store import create_session


def test_final_unresolved_clarification_transitions_to_human_review():
    session_id = create_session("There is a problem, abeg help me.")
    request = ClarifyRequest(answer="I am still not sure", consent=False)

    intake_clarify(session_id, request)
    intake_clarify(session_id, request)
    result = intake_clarify(session_id, request)

    assert result["status"] == "human_review"
    assert result["rounds_remaining"] == 0
    assert result["clarifying_question"] is None
    assert result["artifact"] is None
    assert any("human" in reason.lower() for reason in result["reasons"])
