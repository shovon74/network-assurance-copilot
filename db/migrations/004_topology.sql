-- 004: network topology (which node sits behind which)
CREATE TABLE IF NOT EXISTS topology_nodes (
    node_id   TEXT PRIMARY KEY,
    domain    TEXT NOT NULL CHECK (domain IN ('RAN', 'TRANSPORT', 'CORE')),
    node_type TEXT NOT NULL,
    parent_id TEXT REFERENCES topology_nodes(node_id)
);
