-- 002: core tables for incidents and alarms

CREATE TABLE IF NOT EXISTS incidents (
    id          BIGSERIAL PRIMARY KEY,
    domain      TEXT NOT NULL CHECK (domain IN ('RAN', 'TRANSPORT', 'CORE')),
    severity    TEXT NOT NULL CHECK (severity IN ('critical', 'major', 'minor', 'warning')),
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'noise')),
    opened_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS alarms (
    id          BIGSERIAL PRIMARY KEY,
    raised_at   TIMESTAMPTZ NOT NULL,
    node_id     TEXT NOT NULL,
    domain      TEXT NOT NULL CHECK (domain IN ('RAN', 'TRANSPORT', 'CORE')),
    alarm_type  TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK (severity IN ('critical', 'major', 'minor', 'warning')),
    message     TEXT,
    incident_id BIGINT REFERENCES incidents(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alarms_raised_at ON alarms (raised_at);
CREATE INDEX IF NOT EXISTS idx_alarms_node_id   ON alarms (node_id);
CREATE INDEX IF NOT EXISTS idx_alarms_incident  ON alarms (incident_id);
