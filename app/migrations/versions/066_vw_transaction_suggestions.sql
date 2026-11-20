-- Suggested transactions: your recurring transaction patterns, ranked, so
-- one can be turned into a new transaction in a click. Nothing is stored --
-- a suggestion is just a group of past transactions that share a name,
-- type, currency, category and both accounts, so it is always in step with
-- what was actually recorded.
--
-- score is recency-weighted frequency: every past use counts for
-- exp(-age_days / 90), so a pattern used constantly last month outranks one
-- used the same number of times years ago. The time-of-day boost depends on
-- the caller's timezone, so it lives in app/db/transaction_suggestion.py,
-- not here.
--
-- origin_transaction_id is the most recent transaction in the group; the
-- add page prefills from it (tags, budgets and everything else), and its
-- locations/last_amount are surfaced here for display. Both accounts must
-- still be active, otherwise the suggestion couldn't be saved anyway.
--
-- security_invoker so RLS evaluates against the calling role; user_id is
-- also a grouping column and the query filters on it explicitly, since a
-- shared budget can make other members' transactions visible to RLS.
CREATE VIEW dompet.vw_transaction_suggestions WITH (security_invoker = true) AS
SELECT
    t.user_id,
    t.name,
    t.type,
    t.currency_code AS currency,
    t.category_id,
    c.name AS category,
    t.source_account_id,
    sa.name AS source_account,
    t.destination_account_id,
    da.name AS destination_account,
    COUNT(*) AS times_used,
    COUNT(*) FILTER (WHERE t.datetime >= NOW() - INTERVAL '90 days') AS used_last_90d,
    MAX(t.datetime) AS last_used,
    MODE() WITHIN GROUP (ORDER BY t.amount) AS typical_amount,
    (ARRAY_AGG(t.amount ORDER BY t.datetime DESC, t.created_at DESC))[1] AS last_amount,
    (ARRAY_AGG(t.id ORDER BY t.datetime DESC, t.created_at DESC))[1] AS origin_transaction_id,
    (ARRAY_AGG(t.source_location_id ORDER BY t.datetime DESC, t.created_at DESC))[1] AS source_location_id,
    (ARRAY_AGG(t.destination_location_id ORDER BY t.datetime DESC, t.created_at DESC))[1] AS destination_location_id,
    SUM(EXP(-EXTRACT(EPOCH FROM (NOW() - t.datetime)) / 86400.0 / 90.0)) AS score
FROM dompet.transactions t
JOIN dompet.accounts sa ON sa.id = t.source_account_id AND sa.is_active
JOIN dompet.accounts da ON da.id = t.destination_account_id AND da.is_active
LEFT JOIN dompet.categories c ON c.id = t.category_id
WHERE t.is_active
GROUP BY
    t.user_id, t.name, t.type, t.currency_code, t.category_id, c.name,
    t.source_account_id, sa.name, t.destination_account_id, da.name;

GRANT SELECT ON dompet.vw_transaction_suggestions TO web_user;
