-- Bills module. Two layers: dompet.bill_series holds a recurring
-- definition (no due date of its own -- just the recurrence rule and an
-- anchor), dompet.bills holds one row per actual occurrence, whether it
-- came from a series (series_id set) or was created standalone
-- (series_id NULL). Occurrences are never mutated to "roll forward" --
-- a new occurrence is a new row, generated lazily on read (see
-- app/db/bill.py's sync step), so a missed cycle stays in history
-- instead of being overwritten.
--
-- Paid/unpaid status is intentionally not a column on dompet.bills -- it's
-- derived from dompet.bill_payments, a many-to-many mapping to
-- dompet.transactions (nullable transaction_id, since linking a payment to
-- a transaction is optional). Multiple payments can apply to one bill
-- (partial payments) and one transaction can fund multiple bills (a single
-- combined payment split across bills) -- both already fall out of this
-- just being a plain mapping table with its own amount_paid per row,
-- without any uniqueness constraint tying the two sides together.

CREATE TABLE IF NOT EXISTS dompet.bill_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,

    name VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00
        CHECK (amount >= 0),
    currency_code CHAR(3) NOT NULL
        REFERENCES dompet.currencies (code),
    category_id UUID
        REFERENCES dompet.categories (id),
    account_id UUID
        REFERENCES dompet.accounts (id),

    -- Every occurrence's due date is anchor_date + k * (recurrence_count
    -- recurrence_unit) for whichever k is current -- computed fresh from
    -- the fixed anchor each time, not by repeatedly adding to a mutable
    -- "last due date", so a monthly bill anchored on the 31st doesn't
    -- drift after a shorter month.
    recurrence_unit VARCHAR(10) NOT NULL
        CHECK (recurrence_unit IN ('day', 'week', 'month', 'year')),
    recurrence_count INT NOT NULL DEFAULT 1
        CHECK (recurrence_count > 0),
    anchor_date DATE NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dompet.bills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    series_id UUID
        REFERENCES dompet.bill_series (id),

    -- Copied in from the series at generation time (or set directly for a
    -- one-off bill) rather than read live from bill_series, so editing a
    -- series later doesn't rewrite the history of cycles that already
    -- happened.
    name VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00
        CHECK (amount >= 0),
    currency_code CHAR(3) NOT NULL
        REFERENCES dompet.currencies (code),
    category_id UUID
        REFERENCES dompet.categories (id),
    account_id UUID
        REFERENCES dompet.accounts (id),

    due_date DATE NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Guards the lazy generator against creating the same occurrence twice
-- (e.g. a race between two concurrent requests both syncing the same
-- series). One-off bills (series_id NULL) are untouched by this -- NULL
-- never conflicts with NULL in a unique index.
CREATE UNIQUE INDEX IF NOT EXISTS bills_series_due_date_unique
    ON dompet.bills (series_id, due_date)
    WHERE series_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_bills_user_active
    ON dompet.bills (user_id)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS dompet.bill_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    bill_id UUID NOT NULL
        REFERENCES dompet.bills (id),
    transaction_id UUID
        REFERENCES dompet.transactions (id),

    amount_paid DECIMAL(10, 2) NOT NULL
        CHECK (amount_paid >= 0),
    paid_date DATE NOT NULL,
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bill_payments_bill_id
    ON dompet.bill_payments (bill_id);

CREATE INDEX IF NOT EXISTS idx_bill_payments_transaction_id
    ON dompet.bill_payments (transaction_id)
    WHERE transaction_id IS NOT NULL;

-- Bills can carry their own attachments (e.g. the actual bill/invoice
-- document) independent of any linked transaction's own attachments --
-- mirrors dompet.transaction_attachments exactly.
CREATE TABLE IF NOT EXISTS dompet.bill_attachments (
    bill_id UUID NOT NULL
        REFERENCES dompet.bills (id),
    attachment_id UUID NOT NULL
        REFERENCES dompet.attachments (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (bill_id, attachment_id)
);

-- RLS: strictly owner-only on every table here, unlike budgets/transactions
-- -- there's no bill-sharing/membership concept, so no SELECT-widening
-- clause. (The one place another budget member can see a bill's name/
-- attachments at all is through a shared transaction's own details --
-- see shared_transaction_details() below -- not through these tables.)
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.bill_series TO web_user;
ALTER TABLE dompet.bill_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.bill_series FORCE ROW LEVEL SECURITY;
CREATE POLICY bill_series_all ON dompet.bill_series
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.bills TO web_user;
ALTER TABLE dompet.bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.bills FORCE ROW LEVEL SECURITY;
CREATE POLICY bills_all ON dompet.bills
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.bill_payments TO web_user;
ALTER TABLE dompet.bill_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.bill_payments FORCE ROW LEVEL SECURITY;
CREATE POLICY bill_payments_all ON dompet.bill_payments
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.bill_attachments TO web_user;
ALTER TABLE dompet.bill_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.bill_attachments FORCE ROW LEVEL SECURITY;
CREATE POLICY bill_attachments_all ON dompet.bill_attachments
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.bills b
        WHERE b.id = bill_attachments.bill_id
          AND b.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.bills b
        WHERE b.id = bill_attachments.bill_id
          AND b.user_id = current_setting('app.current_user_id')::uuid
    ));

-- Search/dropdown view for /bills/search, mirrors vw_accounts/vw_budgets --
-- security_invoker = true so RLS (owner-only, above) evaluates against the
-- calling role, not the view owner. Paid status is derived here (summed
-- from bill_payments vs this occurrence's own amount) rather than stored,
-- since a bill can be partially paid across several payments before it's
-- actually settled.
CREATE VIEW dompet.vw_bills WITH (security_invoker = true) AS
SELECT
    b.id,
    b.name,
    b.due_date,
    b.amount,
    b.currency_code AS currency,
    c.name AS category,
    a.name AS account,
    (b.series_id IS NOT NULL) AS is_recurring,
    COALESCE(p.paid_amount, 0.00) AS paid_amount,
    CASE
        WHEN COALESCE(p.paid_amount, 0.00) >= b.amount THEN 'paid'
        WHEN COALESCE(p.paid_amount, 0.00) > 0 THEN 'partial'
        ELSE 'unpaid'
    END AS status,
    (b.due_date < CURRENT_DATE AND COALESCE(p.paid_amount, 0.00) < b.amount) AS is_overdue,
    (
        SELECT COUNT(*) FROM dompet.bill_attachments ba WHERE ba.bill_id = b.id
    ) AS attachment_count
FROM dompet.bills b
LEFT JOIN dompet.categories c ON c.id = b.category_id
LEFT JOIN dompet.accounts a ON a.id = b.account_id
LEFT JOIN LATERAL (
    SELECT SUM(bp.amount_paid) AS paid_amount
    FROM dompet.bill_payments bp
    WHERE bp.bill_id = b.id
) p ON TRUE
WHERE b.is_active = TRUE;

GRANT SELECT ON dompet.vw_bills TO web_user;

-- Extend the existing shared-transaction mechanism (see
-- 047_shared_transaction_details.sql) so a budget co-member viewing a
-- transaction they don't own, but that happens to pay one of the owner's
-- bills, also sees that bill's name and attachments -- same gating as
-- everything else returned by this function (transaction is shared via a
-- budget the caller is a member of), no new bill-sharing concept.
DROP VIEW IF EXISTS dompet.vw_transactions;
DROP FUNCTION IF EXISTS dompet.shared_transaction_details(uuid);

CREATE FUNCTION dompet.shared_transaction_details(tx_id uuid)
RETURNS TABLE (
    source text,
    destination text,
    category text,
    source_location text,
    destination_location text,
    attachments json,
    bills text[],
    bill_attachments json
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = dompet, pg_temp
AS $$
    SELECT
        src.name::text,
        dst.name::text,
        c.name::text,
        sl.name::text,
        dl.name::text,
        COALESCE(
            (
                SELECT json_agg(json_build_object('id', a.id, 'filename', a.filename) ORDER BY a.filename)
                FROM dompet.transaction_attachments ta
                JOIN dompet.attachments a ON a.id = ta.attachment_id
                WHERE ta.transaction_id = t.id AND a.is_active
            ),
            '[]'::json
        ),
        ARRAY(
            SELECT bl.name
            FROM dompet.bill_payments bp
            JOIN dompet.bills bl ON bl.id = bp.bill_id
            WHERE bp.transaction_id = t.id
            ORDER BY bl.name
        ),
        COALESCE(
            (
                SELECT json_agg(json_build_object('id', att.id, 'filename', att.filename) ORDER BY att.filename)
                FROM dompet.bill_payments bp
                JOIN dompet.bill_attachments ba ON ba.bill_id = bp.bill_id
                JOIN dompet.attachments att ON att.id = ba.attachment_id
                WHERE bp.transaction_id = t.id AND att.is_active
            ),
            '[]'::json
        )
    FROM dompet.transactions t
    LEFT JOIN dompet.accounts src ON src.id = t.source_account_id
    LEFT JOIN dompet.accounts dst ON dst.id = t.destination_account_id
    LEFT JOIN dompet.categories c ON c.id = t.category_id
    LEFT JOIN dompet.locations sl ON sl.id = t.source_location_id
    LEFT JOIN dompet.locations dl ON dl.id = t.destination_location_id
    WHERE t.id = tx_id
      AND t.is_active
      AND t.user_id <> NULLIF(current_setting('app.current_user_id', true), '')::uuid
      AND EXISTS (
          SELECT 1
          FROM dompet.transaction_budgets tb
          JOIN dompet.budget_members bm ON bm.budget_id = tb.budget_id
          WHERE tb.transaction_id = t.id
            AND bm.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
      );
$$;

REVOKE ALL ON FUNCTION dompet.shared_transaction_details(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dompet.shared_transaction_details(uuid) TO web_user;

CREATE VIEW dompet.vw_transactions WITH (security_invoker = true) AS
SELECT
    t.id,
    t.datetime::date AS date,
    t.name,
    t.type,
    t.amount,
    t.currency_code AS currency,
    COALESCE(c.name, sh.category) AS category,
    COALESCE(src.name, sh.source) AS source,
    COALESCE(dst.name, sh.destination) AS destination,
    ARRAY(
        SELECT tag.name
        FROM dompet.transaction_tags tt
        JOIN dompet.tags tag ON tag.id = tt.tag_id
        WHERE tt.transaction_id = t.id
        ORDER BY tag.name
    ) AS tags,
    COALESCE(
        (
            SELECT json_agg(json_build_object('id', att.id, 'filename', att.filename) ORDER BY att.filename)
            FROM dompet.transaction_attachments ta
            JOIN dompet.attachments att ON att.id = ta.attachment_id
            WHERE ta.transaction_id = t.id
        ),
        sh.attachments,
        '[]'::json
    ) AS attachments,
    ARRAY(
        SELECT b.name
        FROM dompet.transaction_budgets tb
        JOIN dompet.budgets b ON b.id = tb.budget_id
        WHERE tb.transaction_id = t.id
        ORDER BY b.name
    ) AS budgets,
    (
        ARRAY(
            SELECT bl.name
            FROM dompet.bill_payments bp
            JOIN dompet.bills bl ON bl.id = bp.bill_id
            WHERE bp.transaction_id = t.id
            ORDER BY bl.name
        ) || COALESCE(sh.bills, ARRAY[]::text[])
    ) AS bills,
    COALESCE(
        (
            SELECT json_agg(x) FROM (
                SELECT json_build_object('id', att.id, 'filename', att.filename) AS x
                FROM dompet.bill_payments bp
                JOIN dompet.bill_attachments ba ON ba.bill_id = bp.bill_id
                JOIN dompet.attachments att ON att.id = ba.attachment_id
                WHERE bp.transaction_id = t.id
                UNION ALL
                SELECT json_array_elements(sh.bill_attachments)
            ) combined
        ),
        '[]'::json
    ) AS bill_attachments,
    t.datetime,
    COALESCE(src_loc.name, sh.source_location) AS source_location,
    COALESCE(dst_loc.name, sh.destination_location) AS destination_location,
    t.user_id
FROM dompet.transactions t
LEFT JOIN dompet.categories c ON c.id = t.category_id
LEFT JOIN dompet.accounts src ON src.id = t.source_account_id
LEFT JOIN dompet.accounts dst ON dst.id = t.destination_account_id
LEFT JOIN dompet.locations src_loc ON src_loc.id = t.source_location_id
LEFT JOIN dompet.locations dst_loc ON dst_loc.id = t.destination_location_id
LEFT JOIN LATERAL dompet.shared_transaction_details(t.id) sh ON TRUE
WHERE t.is_active = TRUE;

GRANT SELECT ON dompet.vw_transactions TO web_user;
