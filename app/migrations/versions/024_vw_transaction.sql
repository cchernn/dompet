-- Replaces the earlier transactions_search view with a richer, human-
-- readable "vw_" search view: joined names instead of ids, and pipe-
-- delimited tag/attachment lists. Active transactions only, matching
-- the existing /transactions list's default.
--
-- security_invoker = true still applies (see 023's comment) -- RLS on
-- every joined table (accounts/categories/tags/attachments, all already
-- covered by 016_web_user_rls.sql) evaluates against the actual querying
-- role, not the view owner.

DROP VIEW IF EXISTS dompet.transactions_search;

CREATE VIEW dompet.vw_transaction WITH (security_invoker = true) AS
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
    ) AS attachments
FROM dompet.transactions t
LEFT JOIN dompet.categories c ON c.id = t.category_id
JOIN dompet.accounts src ON src.id = t.source_account_id
JOIN dompet.accounts dst ON dst.id = t.destination_account_id
WHERE t.is_active = TRUE;

GRANT SELECT ON dompet.vw_transaction TO web_user;
