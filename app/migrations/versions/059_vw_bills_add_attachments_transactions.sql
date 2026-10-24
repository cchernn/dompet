-- /bills/search needs enough to navigate straight to a linked
-- attachment or transaction without a round trip per row -- not a raw
-- presigned S3 URL eagerly generated for every row (same reasoning as
-- _to_attachment_summary in app/handlers/attachment.py: that's expensive
-- and short-lived, so it's only done for a single GET /attachments/{id}),
-- but enough identifying info (id, name, filename) for the frontend to
-- link to GET /attachments/{id} itself. Same idea for transactions: a
-- bill can have several payments, each optionally linked to a different
-- transaction (see dompet.bill_payments' own comment on this being a
-- plain many-to-many mapping), so this is the DISTINCT set of
-- transactions actually linked via a payment, not the payments themselves.
--
-- attachment_count is left as-is for backward compatibility; attachments
-- is new and carries the same count implicitly via its length.

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
    COALESCE(tx.transactions, '[]'::json) AS transactions
FROM dompet.bills b
LEFT JOIN dompet.categories c ON c.id = b.category_id
LEFT JOIN dompet.accounts a ON a.id = b.account_id
LEFT JOIN LATERAL (
    SELECT SUM(bp.amount_paid) AS paid_amount
    FROM dompet.bill_payments bp
    WHERE bp.bill_id = b.id
) p ON TRUE
LEFT JOIN LATERAL (
    SELECT json_agg(
        json_build_object('id', att.id, 'name', att.name, 'filename', att.filename)
        ORDER BY att.name
    ) AS attachments
    FROM dompet.bill_attachments ba
    JOIN dompet.attachments att ON att.id = ba.attachment_id
    WHERE ba.bill_id = b.id AND att.is_active
) att ON TRUE
LEFT JOIN LATERAL (
    -- DISTINCT on the typed columns first, then json_agg the already
    -- deduped rows (json_agg(DISTINCT ...) would need jsonb, which
    -- re-parses numerics and drops trailing zeroes -- e.g. 60.00 becomes
    -- 60.0). amount is cast to text so it round-trips through JSON
    -- exactly as stored instead of as a JSON number, which has no fixed
    -- decimal places at all; Decimal fields parse the string back fine.
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
