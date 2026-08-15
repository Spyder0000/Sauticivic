-- SautiCivic Bridge — Database Schema
-- Applied automatically by docker-compose (mounted into postgres initdb).

-- Track every intake session (supports clarification chains)
CREATE TABLE IF NOT EXISTS intake_sessions (
    session_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source          VARCHAR(20) NOT NULL DEFAULT 'text',  -- 'text', 'voice'
    original_transcript TEXT NOT NULL,
    status          VARCHAR(30) NOT NULL,  -- 'routed', 'needs_clarification', 'system_error'
    final_domain    VARCHAR(30),           -- 'infrastructure', 'legal', NULL if not routed
    clarification_count INT NOT NULL DEFAULT 0
);

-- Every pipeline run (initial + each clarification round) gets a row here
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES intake_sessions(session_id),
    run_number      INT NOT NULL DEFAULT 1,  -- 1 = initial, 2+ = clarification rounds
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    transcript_used TEXT NOT NULL,            -- may include clarification context

    -- Classification
    classified_domain   VARCHAR(30),
    classification_confidence FLOAT,
    classification_scores JSONB,
    classification_reasons TEXT[],

    -- Extraction
    extracted_entities  JSONB,  -- array of {type, value, confidence}

    -- Gate decision
    gate_decision       VARCHAR(20) NOT NULL,  -- 'route', 'abstain'
    gate_reasons        TEXT[] NOT NULL,
    clarifying_question TEXT,   -- set when gate_decision = 'abstain'

    UNIQUE(session_id, run_number)
);

-- Generated artifacts (only created when gate_decision = 'route')
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES pipeline_runs(run_id),
    session_id      UUID NOT NULL REFERENCES intake_sessions(session_id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    artifact_type   VARCHAR(30) NOT NULL,  -- 'municipal_ticket', 'legal_brief'
    content         JSONB NOT NULL,
    tracking_id     VARCHAR(100)           -- e.g. ticket number
);

-- Full audit trail — every decision, every reason, queryable
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    session_id      UUID REFERENCES intake_sessions(session_id),
    run_id          UUID REFERENCES pipeline_runs(run_id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type      VARCHAR(50) NOT NULL,  -- 'intake_started', 'classified', 'gate_decided', 'artifact_generated', 'clarification_requested', 'error'
    details         JSONB NOT NULL DEFAULT '{}'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_runs_session ON pipeline_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
