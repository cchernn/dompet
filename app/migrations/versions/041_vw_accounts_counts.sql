-- Renaming usage_count -> transaction_count isn't a pure column append,
-- so CREATE OR REPLACE VIEW can't do it (errors with "cannot change name
-- of view column") -- drop and recreate instead.
DROP VIEW IF EXISTS dompet.vw_accounts;

CREATE VIEW dompet.vw_accounts WITH (security_invoker = true) AS
SELECT
    a.id, a.code, a.name, a.description,
    (
        SELECT COUNT(*) FROM dompet.transactions t
        WHERE t.source_account_id = a.id OR t.destination_account_id = a.id
    ) AS transaction_count,
    a.type,
    (
        SELECT COUNT(*) FROM dompet.account_locations al WHERE al.account_id = a.id
    ) AS location_count
FROM dompet.accounts a
WHERE a.is_active = TRUE;

GRANT SELECT ON dompet.vw_accounts TO web_user;
