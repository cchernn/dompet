-- Renaming usage_count -> transaction_count isn't a pure column append,
-- so CREATE OR REPLACE VIEW can't do it -- drop and recreate instead.
DROP VIEW IF EXISTS dompet.vw_categories;

CREATE VIEW dompet.vw_categories WITH (security_invoker = true) AS
SELECT
    c.id, c.name, c.parent_id,
    (
        SELECT COUNT(*) FROM dompet.transactions t WHERE t.category_id = c.id
    ) AS transaction_count,
    c.user_id
FROM dompet.categories c
WHERE c.is_active = TRUE;

GRANT SELECT ON dompet.vw_categories TO web_user;
