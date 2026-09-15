"""Tests for artifact generation, audit logging, and the complete intake pipeline.

Complements test_gate.py (which tests the gate decision logic in isolation).
These tests verify that:
  - ROUTED outcomes carry a correctly populated artifact (ticket or brief)
  - ABSTAIN outcomes carry no artifact
  - The JSONL audit log records every outcome with the right shape
  - The artifact generators produce stable, well-formed output

Run from the repo root with:  PYTHONPATH=backend python3 -m pytest backend/tests -q
"""
import json
import os
import tempfile
from pathlib import Path

from app.pipeline import run_intake
from app.schemas import Domain, OutcomeStatus
from app.services.legal_brief_generator import generate_brief
from app.services.ticket_dispatch import generate_ticket
from app.schemas import Entity, EntityType, ExtractionResult


# ========================= ticket_dispatch tests =========================

def test_ticket_has_required_fields():
    extraction = ExtractionResult([
        Entity(EntityType.LOCATION, "Allen Avenue", 0.80),
        Entity(EntityType.COMPLAINT_TYPE, "pothole", 0.90),
    ])
    ticket = generate_ticket("Pothole for Allen Avenue", extraction)
    assert ticket["artifact_type"] == "municipal_ticket"
    assert ticket["tracking_id"].startswith("TKT-")
    assert ticket["status"] == "draft_ready_for_confirmation"
    assert ticket["is_draft"] is True
    assert ticket["case_id"].startswith("CASE-")
    assert ticket["location"] == "Allen Avenue"
    assert ticket["complaint_type"] == "pothole"
    assert ticket["description"] == "Pothole for Allen Avenue"
    assert "created_at" in ticket
    assert "local_created_at" in ticket


def test_ticket_missing_entities_uses_unspecified():
    extraction = ExtractionResult([])
    ticket = generate_ticket("Some complaint", extraction)
    assert ticket["location"] == "unspecified"
    assert ticket["complaint_type"] == "unspecified"


def test_ticket_tracking_id_is_deterministic():
    extraction = ExtractionResult([])
    t1 = generate_ticket("Same input", extraction)
    t2 = generate_ticket("Same input", extraction)
    # Same transcript -> same hash portion (date may differ in edge cases,
    # but within the same test run it won't).
    assert t1["tracking_id"] == t2["tracking_id"]


# ========================= legal_brief tests =========================

def test_brief_has_required_fields():
    extraction = ExtractionResult([
        Entity(EntityType.PARTY, "landlord", 0.85),
        Entity(EntityType.GRIEVANCE_TYPE, "eviction", 0.90),
    ])
    brief = generate_brief("My landlord wan evict me", extraction)
    assert brief["artifact_type"] == "legal_brief"
    assert brief["brief_id"].startswith("BRIEF-")
    assert brief["status"] == "draft_ready_for_confirmation"
    assert brief["is_draft"] is True
    assert brief["case_id"].startswith("CASE-")
    assert brief["respondent"] == "landlord"
    assert brief["grievance_type"] == "eviction"
    assert brief["statement_of_facts"] == "My landlord wan evict me"
    assert "created_at" in brief
    assert "local_created_at" in brief


def test_brief_missing_entities_uses_unspecified():
    extraction = ExtractionResult([])
    brief = generate_brief("Some legal complaint", extraction)
    assert brief["respondent"] == "unspecified"
    assert brief["grievance_type"] == "unspecified"


# ================ pipeline integration: artifact populated ================

def test_routed_infra_has_populated_artifact():
    out = run_intake("There is a big pothole on the road for Allen Avenue, e don spoil our tyre.")
    assert out.status is OutcomeStatus.ROUTED
    assert out.domain is Domain.INFRASTRUCTURE
    assert out.artifact is not None
    assert out.artifact["artifact_type"] == "municipal_ticket"
    assert out.artifact["tracking_id"].startswith("TKT-")
    assert out.artifact["status"] == "draft_ready_for_confirmation"
    assert "Allen Avenue" in out.artifact["location"]


def test_routed_legal_has_populated_artifact():
    out = run_intake("My landlord wan evict me and refuse to return my rent deposit.")
    assert out.status is OutcomeStatus.ROUTED
    assert out.domain is Domain.LEGAL
    assert out.artifact is not None
    assert out.artifact["artifact_type"] == "legal_brief"
    assert out.artifact["brief_id"].startswith("BRIEF-")
    assert out.artifact["status"] == "draft_ready_for_confirmation"


def test_abstain_has_no_artifact():
    out = run_intake("Abeg I get one small problem, make una help me.")
    assert out.status is OutcomeStatus.NEEDS_CLARIFICATION
    assert out.artifact is None
    assert out.clarifying_question is not None


def test_ambiguous_abstain_has_no_artifact():
    out = run_intake("My landlord refused to fix the burst pipe in the flat.")
    assert out.status is OutcomeStatus.NEEDS_CLARIFICATION
    assert out.artifact is None


# ========================= audit log tests =========================

def test_audit_log_records_routed_outcome():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_audit.jsonl"
        out = run_intake(
            "There is a big pothole on the road for Allen Avenue, e don spoil our tyre.",
            audit_log_path=log_path,
            session_id="test-session-001",
        )
        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["status"] == "routed"
        assert record["session_id"] == "test-session-001"
        assert record["domain"] == "infrastructure"
        assert record["artifact"] is not None
        assert record["artifact"]["artifact_type"] == "municipal_ticket"
        assert record["clarifying_question"] is None
        assert len(record["reasons"]) > 0
        assert len(record["entities"]) > 0


def test_audit_log_records_abstain_outcome():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_audit.jsonl"
        out = run_intake(
            "Abeg I get one small problem, make una help me.",
            audit_log_path=log_path,
            session_id="test-session-002",
        )
        lines = log_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        assert record["status"] == "needs_clarification"
        assert record["artifact"] is None
        assert record["clarifying_question"] is not None


def test_audit_log_appends_multiple_outcomes():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_audit.jsonl"
        run_intake("Big pothole for Allen Avenue.", audit_log_path=log_path)
        run_intake("My landlord wan evict me.", audit_log_path=log_path)
        run_intake("Abeg help me o.", audit_log_path=log_path)
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 3
        # Each line is valid JSON
        for line in lines:
            json.loads(line)
