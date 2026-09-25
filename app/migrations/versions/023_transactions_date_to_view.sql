-- Drops the raw `date` column now that `datetime` (022) covers it -- date
-- becomes a derived concept for searching/reporting via a view, not a
-- second persisted column.

DROP INDEX IF EXISTS dompet.idx_transactions_user_date;
CREATE INDEX IF NOT EXISTS idx_transactions_user_datetime
    ON dompet.transactions (user_id, datetime DESC);

ALTER TABLE dompet.transactions DROP COLUMN date;

-- security_invoker is essential here: without it, this view (owned by
-- postgres, a superuser that bypasses RLS) would run with the owner's RLS
-- bypass instead of the querying role's, silently leaking every user's
-- rows to anyone granted SELECT on it. With security_invoker, RLS on the
-- underlying dompet.transactions evaluates against the actual caller
-- (web_user), identical to querying the base table directly.
CREATE VIEW dompet.transactions_search WITH (security_invoker = true) AS
SELECT id, user_id, datetime::date AS date, datetime, name, type, amount,
       currency_code, category_id, source_account_id, destination_account_id,
       is_active, created_at, updated_at
FROM dompet.transactions;

GRANT SELECT ON dompet.transactions_search TO web_user;
