-- 005: RAG vector store for runbooks and past incidents

CREATE TABLE IF NOT EXISTS runbook_chunks (
    id          BIGSERIAL PRIMARY KEY,
    doc_id      TEXT NOT NULL,
    doc_type    TEXT NOT NULL CHECK (doc_type IN ('runbook', 'past_incident')),
    title       TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(384) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (doc_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_runbook_chunks_doc_id
    ON runbook_chunks (doc_id);

CREATE INDEX IF NOT EXISTS idx_runbook_chunks_embedding_hnsw
    ON runbook_chunks USING hnsw (embedding vector_cosine_ops);
