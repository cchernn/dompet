CREATE OR REPLACE VIEW dompet.vw_accounts WITH (security_invoker = true) AS
SELECT
    a.id, a.code, a.name, a.description,
    (
        SELECT COUNT(*) FROM dompet.transactions t
        WHERE t.source_account_id = a.id OR t.destination_account_id = a.id
    ) AS usage_count,
    a.type
FROM dompet.accounts a
WHERE a.is_active = TRUE;
