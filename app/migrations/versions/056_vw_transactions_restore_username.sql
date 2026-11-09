-- 052_create_bills.sql rewrote dompet.vw_transactions to add bills/
-- bill_attachments, but copied the body from a definition that predates
-- 049_search_results_add_username.sql -- it dropped the
-- "LEFT JOIN dompet.vw_users_public u" join and the trailing u.username/
-- u.display_name columns, even though its own comment claimed the body
-- was copied from the view's live definition. TransactionSearchResult
-- (app/models/transaction_search.py) requires both fields, so
-- /transactions/search broke silently for every row.
--
-- Fix: re-add the join and the two columns, change nothing else.

DROP VIEW IF EXISTS dompet.vw_transactions;

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
    t.user_id,
    u.username,
    u.display_name
FROM dompet.transactions t
LEFT JOIN dompet.categories c ON c.id = t.category_id
LEFT JOIN dompet.accounts src ON src.id = t.source_account_id
LEFT JOIN dompet.accounts dst ON dst.id = t.destination_account_id
LEFT JOIN dompet.locations src_loc ON src_loc.id = t.source_location_id
LEFT JOIN dompet.locations dst_loc ON dst_loc.id = t.destination_location_id
LEFT JOIN LATERAL dompet.shared_transaction_details(t.id) sh ON TRUE
LEFT JOIN dompet.vw_users_public u ON u.id = t.user_id
WHERE t.is_active = TRUE;

GRANT SELECT ON dompet.vw_transactions TO web_user;
