-- 007: Evaluation benchmark runs and comparative metrics

CREATE TABLE IF NOT EXISTS eval_runs (
    id                    BIGSERIAL PRIMARY KEY,
    run_label             TEXT NOT NULL,
    total_incidents       INT NOT NULL,
    total_raw_alarms      INT NOT NULL,
    open_incidents        INT NOT NULL,
    noise_incidents       INT NOT NULL,
    rca_evaluated         INT NOT NULL,
    cause_accuracy        REAL NOT NULL,
    node_accuracy         REAL NOT NULL,
    full_accuracy         REAL NOT NULL,
    auto_remediated_count INT NOT NULL,
    automation_rate       REAL NOT NULL,
    baseline_mttr_min     REAL NOT NULL,
    agent_mttr_min        REAL NOT NULL,
    mttr_reduction_pct    REAL NOT NULL,
    tickets_avoided_pct   REAL NOT NULL,
    summary_metrics       JSONB NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

