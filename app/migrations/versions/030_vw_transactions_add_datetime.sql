-- vw_transactions only ever exposed the derived `date` (day precision),
-- never the underlying `datetime` -- so /transactions/search's ordering
-- could only ever be day-precise, with no defined tiebreak for same-day
-- transactions. Adds datetime as a real output column (pure addition,
-- CREATE OR REPLACE is fine here, no type change) so results can be
-- ordered with full precision, same as GET /transactions already is.

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
    ) AS budgets,
    t.datetime
FROM dompet.transactions t
LEFT JOIN dompet.categories c ON c.id = t.category_id
JOIN dompet.accounts src ON src.id = t.source_account_id
JOIN dompet.accounts dst ON dst.id = t.destination_account_id
WHERE t.is_active = TRUE;
