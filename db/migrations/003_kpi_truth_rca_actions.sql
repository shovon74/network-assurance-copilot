-- 003: KPIs, ground truth, RCA results, remediation actions

CREATE TABLE IF NOT EXISTS kpi_samples (
    id         BIGSERIAL PRIMARY KEY,
    sampled_at TIMESTAMPTZ NOT NULL,
    node_id    TEXT NOT NULL,
    metric     TEXT NOT NULL,
    value      DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_kpi_node_metric_time
    ON kpi_samples (node_id, metric, sampled_at);

-- Used ONLY by the evaluation harness. Agents must never query this table.
CREATE TABLE IF NOT EXISTS ground_truth (
    id               BIGSERIAL PRIMARY KEY,
    scenario_type    TEXT NOT NULL,
    root_cause       TEXT NOT NULL,
    root_cause_node  TEXT,
    correct_runbook  TEXT,
    expected_severity TEXT CHECK (expected_severity IN ('critical', 'major', 'minor', 'warning')),
    is_noise         BOOLEAN NOT NULL DEFAULT FALSE,
    affected_nodes   TEXT[] NOT NULL DEFAULT '{}',
    started_at       TIMESTAMPTZ NOT NULL,
    ended_at         TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS rca_results (
    id                  BIGSERIAL PRIMARY KEY,
    incident_id         BIGINT NOT NULL REFERENCES incidents(id),
    root_cause          TEXT NOT NULL,
    root_cause_node     TEXT,
    confidence          REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence            JSONB NOT NULL DEFAULT '[]',
    recommended_runbook TEXT,
    model               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rca_incident ON rca_results (incident_id);

CREATE TABLE IF NOT EXISTS actions (
    id               BIGSERIAL PRIMARY KEY,
    incident_id      BIGINT NOT NULL REFERENCES incidents(id),
    action_type      TEXT NOT NULL,
    risk_level       TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    status           TEXT NOT NULL DEFAULT 'pending_approval'
                     CHECK (status IN ('pending_approval', 'approved', 'rejected', 'executed', 'failed')),
    auto_executed    BOOLEAN NOT NULL DEFAULT FALSE,
    post_check_passed BOOLEAN,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    executed_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_actions_incident ON actions (incident_id);
