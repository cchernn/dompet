-- Scheduled bills that need a document before they can be trusted.
--
-- Some recurring bills (utilities, say) are only valid once the actual
-- bill/statement has arrived, so a series can be flagged requires_document.
-- Each generated occurrence copies the flag (like amount/category, so editing
-- the series later doesn't rewrite past occurrences). One-off bills never
-- need one -- the CHECK keeps it to bills that came from a series.
--
-- document_status is derived, not stored:
--   not_required  the occurrence doesn't need a document
--   confirmed     it does and one has arrived: either an attachment is linked
--                 to the bill itself (attachments that only reach it through
--                 a payment's transaction are receipts, not the bill, so they
--                 don't count) or document_confirmed_date was set by hand
--   awaiting      it does and neither has happened yet
-- document_confirmed_via says which of the two applied (attachment wins when
-- both). Payment status (unpaid/partial/paid) and is_overdue are unchanged.

ALTER TABLE dompet.bill_series
    ADD COLUMN requires_document BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE dompet.bills
    ADD COLUMN requires_document BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN document_confirmed_date DATE,
    ADD CONSTRAINT bills_requires_document_needs_series
        CHECK (NOT requires_document OR series_id IS NOT NULL);

-- Same as 067's vw_bills (the latest definition), with the document columns
-- appended.
CREATE OR REPLACE VIEW dompet.vw_bills WITH (security_invoker = true) AS
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
    ) AS attachment_count,
    b.bill_date,
    COALESCE(att.attachments, '[]'::json) AS attachments,
    COALESCE(tx.transaction_count, 0) AS transaction_count,
    COALESCE(tx.transactions, '[]'::json) AS transactions,
    b.series_id,
    b.user_id,
    b.requires_document,
    CASE
        WHEN NOT b.requires_document THEN 'not_required'
        WHEN doc.has_attachment OR b.document_confirmed_date IS NOT NULL THEN 'confirmed'
        ELSE 'awaiting'
    END AS document_status,
    b.document_confirmed_date,
    CASE
        WHEN NOT b.requires_document THEN NULL
        WHEN doc.has_attachment THEN 'attachment'
        WHEN b.document_confirmed_date IS NOT NULL THEN 'manual'
    END AS document_confirmed_via
FROM dompet.bills b
LEFT JOIN dompet.categories c ON c.id = b.category_id
LEFT JOIN dompet.accounts a ON a.id = b.account_id
LEFT JOIN LATERAL (
    SELECT SUM(bp.amount_paid) AS paid_amount
    FROM dompet.bill_payments bp
    WHERE bp.bill_id = b.id
) p ON TRUE
LEFT JOIN LATERAL (
    SELECT EXISTS (
        SELECT 1
        FROM dompet.bill_attachments ba
        JOIN dompet.attachments att ON att.id = ba.attachment_id AND att.is_active
        WHERE ba.bill_id = b.id
    ) AS has_attachment
) doc ON TRUE
LEFT JOIN LATERAL (
    SELECT json_agg(row_to_json(dedup) ORDER BY dedup.name) AS attachments
    FROM (
        SELECT
            att.id,
            att.name,
            att.filename,
            array_agg(DISTINCT links.source) AS linked_via
        FROM (
            SELECT ba.attachment_id, 'bill' AS source
            FROM dompet.bill_attachments ba
            WHERE ba.bill_id = b.id
            UNION ALL
            SELECT ta.attachment_id, 'transaction' AS source
            FROM dompet.bill_payments bp
            JOIN dompet.transaction_attachments ta ON ta.transaction_id = bp.transaction_id
            WHERE bp.bill_id = b.id
        ) links
        JOIN dompet.attachments att ON att.id = links.attachment_id AND att.is_active
        GROUP BY att.id, att.name, att.filename
    ) dedup
) att ON TRUE
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS transaction_count,
        json_agg(row_to_json(dedup) ORDER BY dedup.datetime) AS transactions
    FROM (
        SELECT DISTINCT t.id, t.name, t.datetime, t.amount::text AS amount, t.currency_code
        FROM dompet.bill_payments bp
        JOIN dompet.transactions t ON t.id = bp.transaction_id AND t.is_active
        WHERE bp.bill_id = b.id
    ) dedup
) tx ON TRUE
WHERE b.is_active = TRUE;

GRANT SELECT ON dompet.vw_bills TO web_user;

-- Same as 067's vw_bill_groups with requires_document and
-- awaiting_document_count appended (a one-off is never awaiting).
CREATE OR REPLACE VIEW dompet.vw_bill_groups WITH (security_invoker = true) AS
SELECT
    'series'::text AS kind,
    s.id,
    s.user_id,
    s.name,
    COALESCE(l.amount, s.amount) AS amount,
    s.currency_code AS currency,
    c.name AS category,
    a.name AS account,
    s.recurrence_unit,
    s.recurrence_count,
    s.is_active,
    COALESCE(g.occurrence_count, 0) AS occurrence_count,
    COALESCE(g.unpaid_count, 0) AS unpaid_count,
    COALESCE(g.overdue_count, 0) AS overdue_count,
    g.next_due_date,
    l.status AS latest_status,
    l.bill_date AS latest_bill_date,
    s.requires_document,
    COALESCE(g.awaiting_document_count, 0) AS awaiting_document_count
FROM dompet.bill_series s
LEFT JOIN dompet.categories c ON c.id = s.category_id
LEFT JOIN dompet.accounts a ON a.id = s.account_id
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS occurrence_count,
        COUNT(*) FILTER (WHERE v.status <> 'paid') AS unpaid_count,
        COUNT(*) FILTER (WHERE v.is_overdue) AS overdue_count,
        MIN(v.due_date) FILTER (WHERE v.status <> 'paid') AS next_due_date,
        COUNT(*) FILTER (WHERE v.document_status = 'awaiting') AS awaiting_document_count
    FROM dompet.vw_bills v
    WHERE v.series_id = s.id
) g ON TRUE
LEFT JOIN LATERAL (
    SELECT v.amount, v.status, v.bill_date
    FROM dompet.vw_bills v
    WHERE v.series_id = s.id
    ORDER BY v.bill_date DESC
    LIMIT 1
) l ON TRUE
-- A deactivated series stays listed while it still has unpaid occurrences.
WHERE s.is_active OR COALESCE(g.unpaid_count, 0) > 0

UNION ALL

SELECT
    'one_off'::text,
    b.id,
    b.user_id,
    b.name,
    b.amount,
    b.currency,
    b.category,
    b.account,
    NULL::varchar,
    NULL::int,
    TRUE,
    1::bigint,
    (b.status <> 'paid')::int::bigint,
    b.is_overdue::int::bigint,
    CASE WHEN b.status <> 'paid' THEN b.due_date END,
    b.status,
    b.bill_date,
    FALSE,
    0::bigint
FROM dompet.vw_bills b
WHERE b.series_id IS NULL;

GRANT SELECT ON dompet.vw_bill_groups TO web_user;
