-- /bills/search's attachments should surface not just attachments
-- linked to the bill itself (bill_attachments) but also attachments on
-- any transaction linked to the bill via a payment (transaction_attachments)
-- -- e.g. a receipt photo attached to the paying transaction, not the
-- bill. Union both sources, dedupe by attachment id (the same attachment
-- could in principle be linked both ways), and tag each one with
-- linked_via so the frontend knows which unlink endpoint applies:
-- DELETE /bills/{id}/attachments/{attachment_id} only removes a
-- bill-direct link, not a transaction one.
--
-- attachment_count is left unchanged (bill-direct links only, per its
-- existing documented meaning) -- it no longer equals attachments'
-- length, which is now the merged superset.

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
