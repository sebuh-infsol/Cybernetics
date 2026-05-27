-- Cybernetics initial schema

CREATE TABLE IF NOT EXISTS patterns (
    id          SERIAL PRIMARY KEY,
    signature   VARCHAR(512) NOT NULL UNIQUE,
    diagnosis   VARCHAR(2048),
    action      VARCHAR(2048),
    outcome     VARCHAR(64),
    occurrence_count INTEGER DEFAULT 1,
    last_seen   TIMESTAMPTZ DEFAULT now(),
    metadata    JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_patterns_signature ON patterns (signature);
CREATE INDEX IF NOT EXISTS idx_patterns_last_seen ON patterns (last_seen);

CREATE TABLE IF NOT EXISTS incidents (
    id           SERIAL PRIMARY KEY,
    service      VARCHAR(256) NOT NULL,
    problem_title VARCHAR(512),
    diagnosis    VARCHAR(2048),
    action       VARCHAR(2048),
    outcome      VARCHAR(64),
    issue_iid    VARCHAR(64),
    judge_score  VARCHAR(32),
    session_id   VARCHAR(128),
    created_at   TIMESTAMPTZ DEFAULT now(),
    payload      JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_incidents_service_created ON incidents (service, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_session ON incidents (session_id);
