CREATE TABLE IF NOT EXISTS dompet.transaction_tags (
    transaction_id UUID NOT NULL
        REFERENCES dompet.transactions (id) ON DELETE CASCADE,
    tag_id UUID NOT NULL
        REFERENCES dompet.tags (id) ON DELETE CASCADE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (transaction_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag_id
    ON dompet.transaction_tags (tag_id);
