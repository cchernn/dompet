-- Statements module, modeled on bills (see 052_create_bills.sql). Two
-- layers: dompet.statement_series holds a recurring schedule for one
-- account (the recurrence rule plus an anchor), dompet.statements holds
-- one row per expected-or-received statement, whether it was generated
-- from a series (series_id set) or entered standalone (series_id NULL).
-- Occurrences are generated lazily on read (see app/db/statement.py's
-- sync step), and never rewritten to "roll forward" -- a missed cycle
-- stays in history as overdue.
--
-- Received/overdue status is intentionally not a column -- it's derived
-- from received_date and statement_date, so there's nothing to keep in
-- step.

CREATE TABLE IF NOT EXISTS dompet.statement_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    account_id UUID NOT NULL
        REFERENCES dompet.accounts (id),

    -- Copied onto each generated statement so balances recorded later have
    -- a currency without the caller repeating it every cycle.
    currency_code CHAR(3)
        REFERENCES dompet.currencies (code),

    -- Every occurrence's statement_date is anchor_date + k * (recurrence_count
    -- recurrence_unit), computed fresh from the fixed anchor each time, not
    -- by adding to the previous occurrence, so a monthly statement
    -- anchored on the 31st doesn't drift after a shorter month.
    recurrence_unit VARCHAR(10) NOT NULL
        CHECK (recurrence_unit IN ('day', 'week', 'month', 'year')),
    recurrence_count INT NOT NULL DEFAULT 1
        CHECK (recurrence_count > 0),
    anchor_date DATE NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- An account only ever has one active schedule -- two would just generate
-- duplicate expected rows for the same statement.
CREATE UNIQUE INDEX IF NOT EXISTS statement_series_account_active_unique
    ON dompet.statement_series (account_id)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS dompet.statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    series_id UUID
        REFERENCES dompet.statement_series (id),
    account_id UUID NOT NULL
        REFERENCES dompet.accounts (id),

    -- The date the statement is issued (or expected to be). For a generated
    -- occurrence the period is derived from the recurrence rule: it ends on
    -- statement_date and starts the day after the previous occurrence's
    -- statement_date. Both stay editable afterward.
    statement_date DATE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL
        CHECK (period_end >= period_start),

    -- NULL until the statement has actually been received.
    received_date DATE,

    -- Signed, since a credit card or loan statement can legitimately close
    -- negative. Both optional so statements with no balance still work.
    opening_balance DECIMAL(14, 2),
    closing_balance DECIMAL(14, 2),
    currency_code CHAR(3)
        REFERENCES dompet.currencies (code),
    notes TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Guards the lazy generator against creating the same occurrence twice
-- (e.g. a race between two concurrent requests both syncing the same
-- series). Standalone statements (series_id NULL) are untouched by this.
CREATE UNIQUE INDEX IF NOT EXISTS statements_series_statement_date_unique
    ON dompet.statements (series_id, statement_date)
    WHERE series_id IS NOT NULL;

-- Also blocks a second active statement for the same account and period,
-- so a statement entered by hand before a series existed isn't duplicated
-- by the generator (which skips on any conflict).
CREATE UNIQUE INDEX IF NOT EXISTS statements_account_period_unique
    ON dompet.statements (account_id, period_start, period_end)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_statements_user_active
    ON dompet.statements (user_id)
    WHERE is_active = TRUE;

-- Mirrors dompet.bill_attachments: the statement document itself.
CREATE TABLE IF NOT EXISTS dompet.statement_attachments (
    statement_id UUID NOT NULL
        REFERENCES dompet.statements (id),
    attachment_id UUID NOT NULL
        REFERENCES dompet.attachments (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (statement_id, attachment_id)
);

-- RLS: strictly owner-only on every table, same as bills -- no sharing.
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.statement_series TO web_user;
ALTER TABLE dompet.statement_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.statement_series FORCE ROW LEVEL SECURITY;
CREATE POLICY statement_series_all ON dompet.statement_series
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.statements TO web_user;
ALTER TABLE dompet.statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.statements FORCE ROW LEVEL SECURITY;
CREATE POLICY statements_all ON dompet.statements
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.statement_attachments TO web_user;
ALTER TABLE dompet.statement_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.statement_attachments FORCE ROW LEVEL SECURITY;
CREATE POLICY statement_attachments_all ON dompet.statement_attachments
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.statements s
        WHERE s.id = statement_attachments.statement_id
          AND s.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.statements s
        WHERE s.id = statement_attachments.statement_id
          AND s.user_id = current_setting('app.current_user_id')::uuid
    ));

ALTER TABLE dompet.operations
    DROP CONSTRAINT operations_entity_type_check;

ALTER TABLE dompet.operations
    ADD CONSTRAINT operations_entity_type_check
    CHECK (entity_type IN (
        'transaction', 'account', 'category', 'location', 'tag', 'attachment', 'budget',
        'bill', 'bill_series', 'statement', 'statement_series'
    ));

-- Search view for /statements/search, mirrors vw_bills -- security_invoker
-- so RLS evaluates against the calling role. Status is derived here:
-- received once received_date is set, overdue once statement_date has
-- passed without one, otherwise pending.
CREATE VIEW dompet.vw_statements WITH (security_invoker = true) AS
SELECT
    s.id,
    s.account_id,
    a.name AS account,
    s.statement_date,
    s.period_start,
    s.period_end,
    s.received_date,
    CASE
        WHEN s.received_date IS NOT NULL THEN 'received'
        WHEN s.statement_date < CURRENT_DATE THEN 'overdue'
        ELSE 'pending'
    END AS status,
    (s.series_id IS NOT NULL) AS is_recurring,
    s.opening_balance,
    s.closing_balance,
    s.currency_code AS currency,
    s.notes,
    COALESCE(att.attachment_count, 0) AS attachment_count,
    COALESCE(att.attachments, '[]'::json) AS attachments
FROM dompet.statements s
JOIN dompet.accounts a ON a.id = s.account_id
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS attachment_count,
        json_agg(
            json_build_object('id', att.id, 'name', att.name, 'filename', att.filename)
            ORDER BY att.name
        ) AS attachments
    FROM dompet.statement_attachments sa
    JOIN dompet.attachments att ON att.id = sa.attachment_id AND att.is_active
    WHERE sa.statement_id = s.id
) att ON TRUE
WHERE s.is_active = TRUE;

GRANT SELECT ON dompet.vw_statements TO web_user;
