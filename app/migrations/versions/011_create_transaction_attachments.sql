CREATE TABLE IF NOT EXISTS dompet.transaction_attachments (
    transaction_id UUID NOT NULL
        REFERENCES dompet.transactions (id) ON DELETE CASCADE,
    attachment_id UUID NOT NULL
        REFERENCES dompet.attachments (id) ON DELETE CASCADE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (transaction_id, attachment_id)
);

CREATE INDEX IF NOT EXISTS idx_transaction_attachments_attachment_id
    ON dompet.transaction_attachments (attachment_id);
