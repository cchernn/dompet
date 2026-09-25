-- Adds a pipe-delimited budgets column, same pattern as tags/attachments.
-- CREATE OR REPLACE VIEW (not DROP+CREATE) since it's a pure column
-- addition at the end -- preserves the existing GRANT and security_invoker
-- setting without needing to redo either.

CREATE OR REPLACE VIEW dompet.vw_transactions WITH (security_invoker = true) AS
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
    (
        SELECT string_agg(att.filename, '|' ORDER BY att.filename)
        FROM dompet.transaction_attachments ta
        JOIN dompet.attachments att ON att.id = ta.attachment_id
        WHERE ta.transaction_id = t.id
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
