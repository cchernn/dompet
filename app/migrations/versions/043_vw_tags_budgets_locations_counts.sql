DROP VIEW IF EXISTS dompet.vw_tags;

CREATE VIEW dompet.vw_tags WITH (security_invoker = true) AS
SELECT
    tg.id, tg.name,
    (
        SELECT COUNT(*) FROM dompet.transaction_tags tt WHERE tt.tag_id = tg.id
    ) AS transaction_count
FROM dompet.tags tg
WHERE tg.is_active = TRUE;

DROP VIEW IF EXISTS dompet.vw_budgets;

CREATE VIEW dompet.vw_budgets WITH (security_invoker = true) AS
SELECT
    b.id, b.name,
    (
        SELECT COUNT(*) FROM dompet.transaction_budgets tb WHERE tb.budget_id = b.id
    ) AS transaction_count
FROM dompet.budgets b
WHERE b.is_active = TRUE;

DROP VIEW IF EXISTS dompet.vw_locations;

CREATE VIEW dompet.vw_locations WITH (security_invoker = true) AS
SELECT
    l.id, l.name, l.type,
    (
        SELECT COUNT(*) FROM dompet.account_locations al WHERE al.location_id = l.id
    ) AS account_count,
    (
        SELECT COUNT(*) FROM dompet.transactions t
        WHERE t.source_location_id = l.id OR t.destination_location_id = l.id
    ) AS transaction_count,
    l.user_id
FROM dompet.locations l
WHERE l.is_active = TRUE;

GRANT SELECT ON dompet.vw_tags TO web_user;
GRANT SELECT ON dompet.vw_budgets TO web_user;
GRANT SELECT ON dompet.vw_locations TO web_user;
