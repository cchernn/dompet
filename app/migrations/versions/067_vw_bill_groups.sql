-- Bills landing page: one row per recurring series and per one-off bill,
-- so the UI can show "Electricity", "Water", a one-off repair bill, etc.
-- first and only open the individual billing items on click.
--
-- vw_bills gains series_id and user_id (appended -- CREATE OR REPLACE VIEW
-- can only add columns at the end) so occurrences can be grouped and
-- filtered by their series. vw_bill_groups builds on it.

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
    b.user_id
FROM dompet.bills b
LEFT JOIN dompet.categories c ON c.id = b.category_id
LEFT JOIN dompet.accounts a ON a.id = b.account_id
LEFT JOIN LATERAL (
    SELECT SUM(bp.amount_paid) AS paid_amount
    FROM dompet.bill_payments bp
    WHERE bp.bill_id = b.id
) p ON TRUE
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
    l.bill_date AS latest_bill_date
FROM dompet.bill_series s
LEFT JOIN dompet.categories c ON c.id = s.category_id
LEFT JOIN dompet.accounts a ON a.id = s.account_id
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS occurrence_count,
        COUNT(*) FILTER (WHERE v.status <> 'paid') AS unpaid_count,
        COUNT(*) FILTER (WHERE v.is_overdue) AS overdue_count,
        MIN(v.due_date) FILTER (WHERE v.status <> 'paid') AS next_due_date
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
    b.bill_date
FROM dompet.vw_bills b
WHERE b.series_id IS NULL;

GRANT SELECT ON dompet.vw_bill_groups TO web_user;
