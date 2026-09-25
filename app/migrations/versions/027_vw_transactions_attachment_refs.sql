-- Attachments become {id, filename} objects (JSON) instead of a plain
-- pipe-delimited filename string, so /transactions/search can link each
-- attachment to a fresh presigned download URL via GET /attachments/{id}
-- without eagerly generating one for every attachment on every search page
-- load (presigned URLs expire, and most rows on a page are never clicked).
--
-- DROP+CREATE (not CREATE OR REPLACE) because changing an existing output
-- column's type isn't allowed via CREATE OR REPLACE VIEW -- re-grants
-- afterward since dropping the view drops its grants too.

DROP VIEW IF EXISTS dompet.vw_transactions;

CREATE VIEW dompet.vw_transactions WITH (security_invoker = true) AS
SELECT
    t.id,
    t.datetime::date AS date,
    t.name,
    t.type,
    t.amount,
    t.currency_code AS currency,
    c.name AS category,
    src.name AS source,
    dst.name AS destination,
    (
        SELECT string_agg(tag.name, '|' ORDER BY tag.name)
        FROM dompet.transaction_tags tt
        JOIN dompet.tags tag ON tag.id = tt.tag_id
        WHERE tt.transaction_id = t.id
    ) AS tags,
    COALESCE(
        (
            SELECT json_agg(json_build_object('id', att.id, 'filename', att.filename) ORDER BY att.filename)
            FROM dompet.transaction_attachments ta
            JOIN dompet.attachments att ON att.id = ta.attachment_id
            WHERE ta.transaction_id = t.id
        ),
        '[]'::json
    ) AS attachments,
    (
        SELECT string_agg(b.name, '|' ORDER BY b.name)
        FROM dompet.transaction_budgets tb
        JOIN dompet.budgets b ON b.id = tb.budget_id
        WHERE tb.transaction_id = t.id
    ) AS budgets
FROM dompet.transactions t
LEFT JOIN dompet.categories c ON c.id = t.category_id
JOIN dompet.accounts src ON src.id = t.source_account_id
JOIN dompet.accounts dst ON dst.id = t.destination_account_id
WHERE t.is_active = TRUE;

GRANT SELECT ON dompet.vw_transactions TO web_user;
