-- 006: Agent runs telemetry and LLM response caching

CREATE TABLE IF NOT EXISTS agent_runs (
    id            BIGSERIAL PRIMARY KEY,
    incident_id   BIGINT NOT NULL REFERENCES incidents(id),
    agent_name    TEXT NOT NULL DEFAULT 'rca_agent',
    model         TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('success', 'failed', 'timeout')),
    tool_calls    JSONB NOT NULL DEFAULT '[]',
    final_output  JSONB,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    latency_ms    INT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_incident
    ON agent_runs (incident_id);

CREATE TABLE IF NOT EXISTS llm_cache (
    prompt_hash   TEXT PRIMARY KEY,
    model         TEXT NOT NULL,
    response_text TEXT NOT NULL,
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
