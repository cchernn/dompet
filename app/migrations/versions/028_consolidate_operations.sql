-- Consolidates transaction_operations into one shared, polymorphic
-- operations log covering every primary entity's lifecycle (accounts,
-- categories, locations, tags, attachments, budgets, transactions).
-- entity_type + entity_id instead of a real FK -- one column can't
-- reference multiple different tables, so this trades away DB-enforced
-- referential integrity (no CASCADE delete, no guarantee entity_id
-- actually exists) for a single log instead of one table per entity --
-- an explicit, accepted tradeoff.

CREATE TABLE dompet.operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL
        CHECK (entity_type IN ('transaction', 'account', 'category', 'location', 'tag', 'attachment', 'budget')),
    entity_id UUID NOT NULL,
    user_id UUID NOT NULL,
    operation_type VARCHAR(255) NOT NULL
        CHECK (operation_type IN ('CREATE', 'UPDATE', 'DEACTIVATE', 'REACTIVATE', 'ROLLBACK', 'DELETE')),
    before_data JSONB,
    after_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_operations_entity ON dompet.operations (entity_type, entity_id);
CREATE INDEX idx_operations_user_id ON dompet.operations (user_id);
CREATE INDEX idx_operations_created_at ON dompet.operations (created_at DESC);

-- Preserve existing ids -- rollback_transaction looks up operations by id.
INSERT INTO dompet.operations (id, entity_type, entity_id, user_id, operation_type, before_data, after_data, created_at, metadata)
SELECT id, 'transaction', transaction_id, user_id, operation_type, before_data, after_data, created_at, metadata
FROM dompet.transaction_operations;

DROP TABLE dompet.transaction_operations;

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.operations TO web_user;
ALTER TABLE dompet.operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.operations FORCE ROW LEVEL SECURITY;
CREATE POLICY operations_all ON dompet.operations
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
