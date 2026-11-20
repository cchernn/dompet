-- Staged transactions: drafts a user prepares before approving them into
-- real transactions. Deliberately a separate table rather than a flag on
-- dompet.transactions -- every summary, trend, insight and budget view
-- reads that table, so a draft living there would count as real spending
-- anywhere a filter was missed.
--
-- Nearly every field is nullable, since a draft can be half-filled;
-- completeness is checked on approval (and surfaced as missing_fields in
-- vw_staged_transactions). Approving creates a brand-new transaction the
-- same way the add flow does and keeps the draft, marked 'approved' and
-- pointing at it, as the audit trail.
--
-- Drafts are private to their owner -- no sharing.

CREATE TABLE IF NOT EXISTS dompet.staged_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,

    status VARCHAR(10) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'approved', 'discarded')),
    -- Where the draft came from. 'import' is reserved for a later phase.
    origin VARCHAR(20) NOT NULL DEFAULT 'manual'
        CHECK (origin IN ('manual', 'suggestion', 'import')),
    -- The transaction a suggestion-sourced draft was copied from, and the
    -- transaction an approved draft turned into. SET NULL so deleting
    -- either side never blocks.
    origin_transaction_id UUID
        REFERENCES dompet.transactions (id) ON DELETE SET NULL,
    approved_transaction_id UUID
        REFERENCES dompet.transactions (id) ON DELETE SET NULL,

    name VARCHAR(255),
    type VARCHAR(255)
        CHECK (type IS NULL OR type IN ('expenditure', 'income', 'transfer')),
    amount NUMERIC(10, 2)
        CHECK (amount IS NULL OR amount >= 0),
    currency_code CHAR(3)
        REFERENCES dompet.currencies (code),
    category_id UUID
        REFERENCES dompet.categories (id),
    source_account_id UUID
        REFERENCES dompet.accounts (id),
    destination_account_id UUID
        REFERENCES dompet.accounts (id),
    source_location_id UUID
        REFERENCES dompet.locations (id),
    destination_location_id UUID
        REFERENCES dompet.locations (id),
    datetime TIMESTAMPTZ,
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staged_transactions_user_status
    ON dompet.staged_transactions (user_id, status, created_at DESC);

-- Same three links a transaction can carry, copied onto the real
-- transaction on approval.
CREATE TABLE IF NOT EXISTS dompet.staged_transaction_tags (
    staged_transaction_id UUID NOT NULL
        REFERENCES dompet.staged_transactions (id) ON DELETE CASCADE,
    tag_id UUID NOT NULL
        REFERENCES dompet.tags (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (staged_transaction_id, tag_id)
);

CREATE TABLE IF NOT EXISTS dompet.staged_transaction_budgets (
    staged_transaction_id UUID NOT NULL
        REFERENCES dompet.staged_transactions (id) ON DELETE CASCADE,
    budget_id UUID NOT NULL
        REFERENCES dompet.budgets (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (staged_transaction_id, budget_id)
);

CREATE TABLE IF NOT EXISTS dompet.staged_transaction_attachments (
    staged_transaction_id UUID NOT NULL
        REFERENCES dompet.staged_transactions (id) ON DELETE CASCADE,
    attachment_id UUID NOT NULL
        REFERENCES dompet.attachments (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (staged_transaction_id, attachment_id)
);

-- RLS: strictly owner-only on every table.
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.staged_transactions TO web_user;
ALTER TABLE dompet.staged_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.staged_transactions FORCE ROW LEVEL SECURITY;
CREATE POLICY staged_transactions_all ON dompet.staged_transactions
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.staged_transaction_tags TO web_user;
ALTER TABLE dompet.staged_transaction_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.staged_transaction_tags FORCE ROW LEVEL SECURITY;
CREATE POLICY staged_transaction_tags_all ON dompet.staged_transaction_tags
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.staged_transactions st
        WHERE st.id = staged_transaction_tags.staged_transaction_id
          AND st.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.staged_transactions st
        WHERE st.id = staged_transaction_tags.staged_transaction_id
          AND st.user_id = current_setting('app.current_user_id')::uuid
    ));

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.staged_transaction_budgets TO web_user;
ALTER TABLE dompet.staged_transaction_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.staged_transaction_budgets FORCE ROW LEVEL SECURITY;
CREATE POLICY staged_transaction_budgets_all ON dompet.staged_transaction_budgets
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.staged_transactions st
        WHERE st.id = staged_transaction_budgets.staged_transaction_id
          AND st.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.staged_transactions st
        WHERE st.id = staged_transaction_budgets.staged_transaction_id
          AND st.user_id = current_setting('app.current_user_id')::uuid
    ));

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.staged_transaction_attachments TO web_user;
ALTER TABLE dompet.staged_transaction_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.staged_transaction_attachments FORCE ROW LEVEL SECURITY;
CREATE POLICY staged_transaction_attachments_all ON dompet.staged_transaction_attachments
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.staged_transactions st
        WHERE st.id = staged_transaction_attachments.staged_transaction_id
          AND st.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.staged_transactions st
        WHERE st.id = staged_transaction_attachments.staged_transaction_id
          AND st.user_id = current_setting('app.current_user_id')::uuid
    ));

ALTER TABLE dompet.operations
    DROP CONSTRAINT operations_entity_type_check;

ALTER TABLE dompet.operations
    ADD CONSTRAINT operations_entity_type_check
    CHECK (entity_type IN (
        'transaction', 'account', 'category', 'location', 'tag', 'attachment', 'budget',
        'bill', 'bill_series', 'statement', 'statement_series', 'staged_transaction'
    ));

-- Search view for /staged-transactions/search -- security_invoker so RLS
-- evaluates against the calling role. missing_fields lists what still
-- blocks approval; is_complete is true when nothing does.
CREATE VIEW dompet.vw_staged_transactions WITH (security_invoker = true) AS
SELECT
    st.id,
    st.status,
    st.origin,
    st.origin_transaction_id,
    st.approved_transaction_id,
    st.name,
    st.type,
    st.amount,
    st.currency_code AS currency,
    c.name AS category,
    st.category_id,
    sa.name AS source_account,
    st.source_account_id,
    da.name AS destination_account,
    st.destination_account_id,
    sl.name AS source_location,
    dl.name AS destination_location,
    st.datetime,
    st.notes,
    array_remove(ARRAY[
        CASE WHEN st.name IS NULL THEN 'name' END,
        CASE WHEN st.type IS NULL THEN 'type' END,
        CASE WHEN st.amount IS NULL THEN 'amount' END,
        CASE WHEN st.currency_code IS NULL THEN 'currency_code' END,
        CASE WHEN st.source_account_id IS NULL THEN 'source_account_id' END,
        CASE WHEN st.destination_account_id IS NULL THEN 'destination_account_id' END,
        CASE WHEN st.datetime IS NULL THEN 'datetime' END
    ], NULL) AS missing_fields,
    (
        st.name IS NOT NULL AND st.type IS NOT NULL AND st.amount IS NOT NULL
        AND st.currency_code IS NOT NULL AND st.source_account_id IS NOT NULL
        AND st.destination_account_id IS NOT NULL AND st.datetime IS NOT NULL
    ) AS is_complete,
    st.created_at,
    st.updated_at
FROM dompet.staged_transactions st
LEFT JOIN dompet.categories c ON c.id = st.category_id
LEFT JOIN dompet.accounts sa ON sa.id = st.source_account_id
LEFT JOIN dompet.accounts da ON da.id = st.destination_account_id
LEFT JOIN dompet.locations sl ON sl.id = st.source_location_id
LEFT JOIN dompet.locations dl ON dl.id = st.destination_location_id;

GRANT SELECT ON dompet.vw_staged_transactions TO web_user;
