-- Backs two things on POST /assistant/query at once: a per-user rate
-- limit (COUNT(*) of recent rows) and basic observability (which tools
-- got called, how many Bedrock rounds a query took, whether it errored).
-- One append-only table instead of two separate mechanisms, since the
-- rate limit's own counter query IS the observability data.

CREATE TABLE dompet.assistant_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_length INT NOT NULL,
    round_count INT NOT NULL,
    tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb,
    stop_reason VARCHAR(50),
    error_type VARCHAR(100),
    latency_ms INT NOT NULL
);

CREATE INDEX idx_assistant_queries_user_created
    ON dompet.assistant_queries (user_id, created_at DESC);

GRANT SELECT, INSERT ON dompet.assistant_queries TO web_user;
ALTER TABLE dompet.assistant_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.assistant_queries FORCE ROW LEVEL SECURITY;
CREATE POLICY assistant_queries_all ON dompet.assistant_queries
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
