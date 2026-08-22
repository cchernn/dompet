CREATE TABLE IF NOT EXISTS dompet.transaction_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL
        REFERENCES dompet.transactions (id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    operation_type VARCHAR(255) NOT NULL
        CHECK (operation_type IN ('create', 'update', 'delete')),
    before_data JSONB,
    after_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transaction_operations_transaction_id
    ON dompet.transaction_operations (transaction_id);

CREATE INDEX IF NOT EXISTS idx_transaction_operations_user_id
    ON dompet.transaction_operations (user_id);

CREATE INDEX IF NOT EXISTS idx_transaction_operations_created_at
    ON dompet.transaction_operations (created_at DESC);
